#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
learning-journal (lj) —— 学习记录与复习系统的原子化操作脚本。

设计原则：LLM 只做"判断与组织内容"，本脚本负责所有可确定性计算的文件操作
（ID 分配、卡片写入、进度统计、复习调度），从而降低每次会话的 token 消耗。

用法：
  lj.py init   --course <课程名> [--docs <教学文档相对路径>] [--chapters <逗号分隔章节>]
                [--open] [--template 编程|语言]
  lj.py add    <JSON 或 --json '...'>           追加一张卡片（自动分配 ID、更新进度与清单）
  lj.py pick   [--chapter <章节>] [--n 5] [--all]  挑复习卡片（优先到期/待复习）
  lj.py mark   --id K-12 --result pass|fail|partial  记录复习结果（记忆曲线推进）
  lj.py due                                       列出今天到期应复习的卡片（会话内提醒用）
  lj.py archive --json '{"K-12":"第四章 智能体经典范式构建",...}'
                                                 聚类归档：把待归档区卡片搬入章节
  lj.py stats                                     重算卡片数/复习分布并刷新进度表
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # learning/ 目录
if BASE_DIR.name == "scripts":
    BASE_DIR = BASE_DIR.parent                      # 脚本在 learning/scripts/ 时向上取 learning/
CONFIG_FILE = BASE_DIR / "学习配置.md"
NOTE_FILE = BASE_DIR / "学习笔记.md"
PROGRESS_FILE = BASE_DIR / "进度表.md"
REVIEW_FILE = BASE_DIR / "复习清单.md"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Ebbinghaus 记忆曲线间隔（天）。阶段 i 答对后，下次复习 = 今天 + INTERVALS[i]
INTERVALS = [1, 2, 4, 7, 15, 30]
MAX_STAGE = len(INTERVALS) - 1
AUTO_COMPLETE_DAYS = 7

# 卡片类型 -> 标签
TYPE_TAGS = {
    "bug": "Bug", "knowledge": "知识点", "concept": "知识点", "syntax": "语法",
    "word": "生词", "grammar": "语法", "expression": "表达", "env": "环境",
    "design": "设计", "other": "其他",
}

# 复习清单表格列：ID | 章节 | 标题 | 状态 | 下次复习 | 阶段 | 锚点
REVIEW_HEADER = "| ID | 章节 | 标题 | 状态 | 下次复习 | 阶段 | 锚点 |\n| --- | --- | --- | --- | --- | --- | --- |"

TODAY = dt.date.today()

def today_str():
    return TODAY.isoformat()

def add_days(d):
    return (TODAY + dt.timedelta(days=d)).isoformat()

def sub_days(d, n):
    return (d - dt.timedelta(days=n)).isoformat()

def fail(msg):
    print(f"[lj] 错误: {msg}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# 配置读写
# ---------------------------------------------------------------------------
def load_config():
    if not CONFIG_FILE.exists():
        fail(f"未找到配置文件 {CONFIG_FILE}，请先运行 lj.py init")
    text = CONFIG_FILE.read_text(encoding="utf-8")
    cfg = {}
    for line in text.splitlines():
        # 兼容 markdown 格式：- **字段**：值
        m = re.match(r"^[-*\s`]*([^:#\n]+?)[*\s`]*[:：]\s*(.*)$", line.strip())
        if m:
            cfg[m.group(1).strip()] = m.group(2).strip()
    return cfg

def cfg_chapters(cfg):
    """解析章节列表字段为 ['章节1', '章节2', ...]"""
    raw = cfg.get("章节列表", cfg.get("章节", ""))
    parts = [p.strip() for p in re.split(r"[|,，;；]", raw) if p.strip()]
    return parts

def cfg_open(cfg):
    return cfg.get("开放式章节", "false").strip().lower() in ("true", "yes", "1", "是")

def cfg_note_file(cfg):
    return BASE_DIR / cfg.get("笔记文件", "学习笔记.md")

def cfg_review_file(cfg):
    return BASE_DIR / cfg.get("复习清单文件", "复习清单.md")

def cfg_progress_file(cfg):
    return BASE_DIR / cfg.get("进度表文件", "进度表.md")

def parse_iso_date(text):
    try:
        return dt.date.fromisoformat(text.strip())
    except Exception:
        return None

# ---------------------------------------------------------------------------
# init —— 生成 learning/ 四件套
# ---------------------------------------------------------------------------
def cmd_init(args):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    course = args.course or "未命名课程"
    docs = args.docs or ""
    template = args.template or "编程"
    chapters = [c.strip() for c in re.split(r"[|,，;；]", args.chapters or "") if c.strip()]

    # 学习配置.md
    chapter_field = " | ".join(chapters) if chapters else "（留空则全部进入待归档区，可用 lj.py archive 聚类）"
    cfg_text = f"""# 学习配置

> 本文件由 lj.py init 生成。进入新课程时，通过对话式初始化填写以下字段。
> 任何 agent（Hermes / Codex / DeepSeek harness 等）应先读取本文件再操作。

- **课程名称**：{course}
- **教学文档位置**：{docs}
- **模板类型**：{template}
- **开放式章节**：{'true' if args.open else 'false'}（true = 章节未知，先入待归档区，每周聚类）
- **章节列表**：{chapter_field}
- **笔记文件**：学习笔记.md
- **进度表文件**：进度表.md
- **复习清单文件**：复习清单.md
- **复习间隔（天）**：1 → 2 → 4 → 7 → 15 → 30（答对推进，答错重置）
"""
    CONFIG_FILE.write_text(cfg_text, encoding="utf-8")

    # 学习笔记.md —— 预建章节骨架
    note_lines = [
        f"# {course} 学习笔记",
        "",
        f"> 由 learning-journal 系统维护（lj.py）。课程：{course}。",
        f"> 卡片格式：`### K-N [类型] 标题` + 字段（问/答/码或例/坑或记/一句话/参考）。",
        "> 新卡片自动进入对应章节；开放式课程先进入「待归档区」，每周聚类归档。",
        "",
    ]
    for ch in chapters:
        note_lines += [f"## {ch}", "", "<!-- 记录区 -->", ""]
    note_lines += ["## 待归档区", "", "<!-- 开放式课程的新卡片先落在这里，每周用 lj.py archive 聚类 -->", ""]
    cfg_note_file(load_config()).write_text("\n".join(note_lines), encoding="utf-8")

    # 进度表.md
    prog_lines = [
        "# 学习进度表",
        "",
        f"> 由 lj.py stats 自动刷新计数。状态：⬜ 未开始 / 📖 学习中 / ✅ 已完成（有卡片即学习中；用户可手动结束；连续 {AUTO_COMPLETE_DAYS} 天未新增卡片自动完成）",
        "",
        "| 章节 | 状态 | 开始日期 | 完成日期 | 卡片数 | 待复习 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for ch in chapters:
        prog_lines.append(f"| {ch} | ⬜ |  |  | 0 | 0 |")
    prog_lines += ["| 待归档区 | ⬜ |  |  | 0 | 0 |", ""]
    PROGRESS_FILE.write_text("\n".join(prog_lines), encoding="utf-8")

    # 复习清单.md
    review_lines = [
        "# 复习清单",
        "",
        "> 由 lj.py 自动维护。状态：⬜ 未复习 / 🔄 待复习 / 📌 薄弱 / ✅ 已掌握",
        "> 阶段 = 记忆曲线进度（0 新卡，1..6 对应 1/2/4/7/15/30 天间隔）。答对推进，答错回 0。",
        "",
        REVIEW_HEADER,
        "",
    ]
    REVIEW_FILE.write_text("\n".join(review_lines), encoding="utf-8")

    print(f"[lj] 初始化完成：{course}")
    print(f"  配置: {CONFIG_FILE}")
    print(f"  笔记: {cfg_note_file(load_config())}")
    print(f"  进度: {PROGRESS_FILE}")
    print(f"  清单: {REVIEW_FILE}")

# ---------------------------------------------------------------------------
# 笔记/清单解析
# ---------------------------------------------------------------------------
def read_note(cfg):
    return cfg_note_file(cfg).read_text(encoding="utf-8")

def find_chapter_pos(text, chapter):
    """返回章节标题所在行号（0 基）；未找到返回 None"""
    for m in re.finditer(r"^## (.+)$", text, re.M):
        if m.group(1).strip() == chapter:
            return m.start()
    # 容错：包含匹配
    for m in re.finditer(r"^## (.+)$", text, re.M):
        if chapter in m.group(1) or m.group(1) in chapter:
            return m.start()
    return None

def next_card_id(text):
    """全局递增 ID：K-N"""
    nums = [int(m) for m in re.findall(r"^### K-(\d+) ", text, re.M)]
    return f"K-{max(nums) + 1 if nums else 1}"

def insert_card(text, chapter, card_block):
    """把卡片插入章节标题之后、下一同级标题之前"""
    pos = find_chapter_pos(text, chapter)
    if pos is None:
        fail(f"笔记中找不到章节「{chapter}」，请检查学习配置.md 的章节列表")
    nxt = text.find("\n## ", pos + 1)
    if nxt == -1:
        nxt = len(text)
    return text[:nxt] + "\n" + card_block + "\n" + text[nxt:]

def parse_review_lines():
    if not REVIEW_FILE.exists():
        return []
    lines = []
    for line in REVIEW_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and not line.startswith("| ---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 7 and re.match(r"^K-\d+$", cells[0]):
                lines.append(cells)
    return lines

def write_review_lines(rows):
    out = [
        "# 复习清单",
        "",
        "> 由 lj.py 自动维护。状态：⬜ 未复习 / 🔄 待复习 / 📌 薄弱 / ✅ 已掌握",
        "> 阶段 = 记忆曲线进度（0 新卡，1..6 对应 1/2/4/7/15/30 天间隔）。答对推进，答错回 0。",
        "",
        REVIEW_HEADER,
        "",
    ]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    out.append("")
    REVIEW_FILE.write_text("\n".join(out), encoding="utf-8")

def review_row(cid, chapter, title, status, due, stage, anchor):
    return [cid, chapter, title, status, due, str(stage), anchor]

# ---------------------------------------------------------------------------
# add —— 追加卡片
# ---------------------------------------------------------------------------
def cmd_add(args):
    cfg = load_config()
    if args.json:
        try:
            data = json.loads(args.json)
        except json.JSONDecodeError:
            fail("--json 不是合法 JSON")
    elif args.card:
        try:
            data = json.loads(args.card)
        except json.JSONDecodeError:
            fail("位置参数不是合法 JSON")
    else:
        raw = sys.stdin.read() if not sys.stdin.isatty() else None
        if not raw or not raw.strip():
            fail("需要卡片内容：lj.py add 'JSON' / --json '...' / 或 stdin 传入 JSON")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            fail("stdin 不是合法 JSON")

    chapter = (data.get("chapter") or "").strip()
    ctype = (data.get("type") or "other").strip().lower()
    title = (data.get("title") or "").strip()
    q = (data.get("q") or "").strip()
    a = (data.get("a") or "").strip()
    code = (data.get("code") or data.get("example") or "").strip()
    point = (data.get("point") or "").strip()
    summary = (data.get("summary") or "").strip()
    ref = (data.get("ref") or "").strip()
    lang = (data.get("lang") or "text").strip()

    if not title:
        fail("缺少 title 字段")
    if not a:
        fail("缺少 a（解答）字段")

    tag = TYPE_TAGS.get(ctype, ctype.capitalize() or "其他")
    note = read_note(cfg)

    # 章节定位：未指定或不在章节列表 → 待归档区
    chapters = cfg_chapters(cfg)
    if chapter and chapter not in chapters:
        if find_chapter_pos(note, chapter) is None:
            print(f"[lj] 提示：章节「{chapter}」不在配置章节列表中，卡片将进入待归档区", file=sys.stderr)
            chapter = ""
    if not chapter:
        chapter = "待归档区"

    cid = next_card_id(note)
    block = f"### {cid} [{tag}] {title}\n"
    if q:
        block += f"- **问**：{q}\n"
    block += f"- **答**：{a}\n"
    block += f"- **创建**：{today_str()}\n"
    if code:
        # 代码/例句逐行加 2 空格缩进，保持与字段对齐
        code_ind = "\n".join(("  " + l) if l.strip() else l for l in code.splitlines())
        is_lang = "语言" in cfg.get("模板类型", "编程")
        block += f"- **{'例' if is_lang else '码'}**：\n  ```{lang}\n{code_ind}\n  ```\n"
    if point:
        key = "记" if "语言" in cfg.get("模板类型", "编程") else "坑"
        block += f"- **{key}**：{point}\n"
    if summary:
        block += f"- **一句话**：{summary}\n"
    if ref:
        block += f"- **参考**：{ref}\n"

    note = insert_card(note, chapter, block)
    cfg_note_file(cfg).write_text(note, encoding="utf-8")

    # 复习清单加行：新卡 ⬜ 未复习，下次 = 今天 + 1 天
    rows = parse_review_lines()
    rows.append(review_row(cid, chapter, f"[{tag}] {title}", "⬜", add_days(1), 0, f"{cfg_note_file(cfg).name}#{cid}"))
    write_review_lines(rows)

    # 进度表卡片数 +1
    stats(cfg)

    print(f"[lj] 已记录 {cid} -> {chapter}")
    print(f"  标题: [{tag}] {title}")
    print(f"  锚点: {cfg_note_file(cfg).name}#{cid}")

# ---------------------------------------------------------------------------
# 进度表刷新（stats 内部）
# ---------------------------------------------------------------------------
def stats(cfg=None):
    cfg = cfg or load_config()
    note = read_note(cfg)
    rows = parse_review_lines()

    # 各章节卡片数（从笔记解析）
    counts = {}
    created_by_ch = {}
    cur = None
    for line in note.splitlines():
        m = re.match(r"^## (.+)$", line)
        if m:
            cur = m.group(1).strip()
            counts.setdefault(cur, 0)
        elif re.match(r"^### K-\d+ ", line) and cur:
            counts[cur] = counts.get(cur, 0) + 1
        elif cur:
            m = re.match(r"^- \*\*创建\*\*：[ ]*(\d{4}-\d{2}-\d{2})$", line)
            if m:
                created_by_ch.setdefault(cur, []).append(m.group(1))

    # 各章节待复习数（清单中状态 != ✅ 且到期）
    due_by_ch = {}
    for r in rows:
        ch, status, due = r[1], r[3], r[4]
        try:
            due_d = dt.date.fromisoformat(due)
        except ValueError:
            due_d = TODAY + dt.timedelta(days=1)
        if status != "✅" and due_d <= TODAY:
            due_by_ch[ch] = due_by_ch.get(ch, 0) + 1

    # 尝试从复习清单为旧卡片补首日信息（旧卡片若仍在阶段0，可由到期日反推创建日）
    for r in rows:
        ch, due, stage = r[1], r[4], r[5]
        if ch in created_by_ch:
            continue
        due_d = parse_iso_date(due)
        if due_d and stage == "0":
            created_by_ch.setdefault(ch, []).append(sub_days(due_d, 1))

    # 重写进度表
    prog = PROGRESS_FILE.read_text(encoding="utf-8") if PROGRESS_FILE.exists() else ""
    existing = {}
    for line in prog.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and not line.startswith("| ---"):
            existing[cells[0]] = cells[1:5]  # 状态, 开始, 完成, (旧卡片数)

    out = [
        "# 学习进度表",
        "",
        f"> 由 lj.py stats 自动刷新计数。状态：⬜ 未开始 / 📖 学习中 / ✅ 已完成（有卡片即学习中；用户可手动结束；连续 {AUTO_COMPLETE_DAYS} 天未新增卡片自动完成）",
        "",
        "| 章节 | 状态 | 开始日期 | 完成日期 | 卡片数 | 待复习 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    chapters = cfg_chapters(cfg)
    all_ch = chapters + [c for c in counts if c not in chapters]
    for ch in all_ch:
        old_st, old_start, old_done, _ = existing.get(ch, ["⬜", "", "", "0"])
        card_count = counts.get(ch, 0)
        created_dates = sorted(parse_iso_date(d) for d in created_by_ch.get(ch, []) if parse_iso_date(d))
        inferred_start = created_dates[0].isoformat() if created_dates else old_start
        latest_date = created_dates[-1] if created_dates else parse_iso_date(old_start)
        if card_count <= 0:
            st, start, done = "⬜", "", ""
        elif old_st == "✅" and old_done:
            st, start, done = "✅", (old_start or inferred_start), old_done
        elif latest_date and (TODAY - latest_date).days >= AUTO_COMPLETE_DAYS:
            st = "✅"
            start = old_start or inferred_start
            done = old_done or add_days(-(TODAY - latest_date).days + AUTO_COMPLETE_DAYS)
            if not parse_iso_date(done):
                done = (latest_date + dt.timedelta(days=AUTO_COMPLETE_DAYS)).isoformat()
        else:
            st, start, done = "📖", (old_start or inferred_start), ""
        out.append(f"| {ch} | {st} | {start} | {done} | {counts.get(ch, 0)} | {due_by_ch.get(ch, 0)} |")
    if "待归档区" not in all_ch:
        old_st, old_start, old_done, _ = existing.get("待归档区", ["⬜", "", "", "0"])
        card_count = counts.get("待归档区", 0)
        created_dates = sorted(parse_iso_date(d) for d in created_by_ch.get("待归档区", []) if parse_iso_date(d))
        inferred_start = created_dates[0].isoformat() if created_dates else old_start
        latest_date = created_dates[-1] if created_dates else parse_iso_date(old_start)
        if card_count <= 0:
            st, start, done = "⬜", "", ""
        elif old_st == "✅" and old_done:
            st, start, done = "✅", (old_start or inferred_start), old_done
        elif latest_date and (TODAY - latest_date).days >= AUTO_COMPLETE_DAYS:
            st = "✅"
            start = old_start or inferred_start
            done = old_done or (latest_date + dt.timedelta(days=AUTO_COMPLETE_DAYS)).isoformat()
        else:
            st, start, done = "📖", (old_start or inferred_start), ""
        out.append(f"| 待归档区 | {st} | {start} | {done} | {counts.get('待归档区', 0)} | {due_by_ch.get('待归档区', 0)} |")
    out.append("")
    PROGRESS_FILE.write_text("\n".join(out), encoding="utf-8")
    return counts, due_by_ch

# ---------------------------------------------------------------------------
# pick —— 挑复习卡片
# ---------------------------------------------------------------------------
def cmd_pick(args):
    cfg = load_config()
    rows = parse_review_lines()
    if not rows:
        print("[lj] 复习清单为空")
        return
    if not args.all:
        # 优先：到期（下次<=今天 且 状态 != ✅）；其次：🔄/📌/⬜
        due_rows = [r for r in rows if r[3] != "✅" and (lambda d: d <= TODAY)(_parse_due(r[4]))]
        pool = due_rows if due_rows else [r for r in rows if r[3] in ("🔄", "📌", "⬜")]
    else:
        pool = rows
    if args.chapter:
        pool = [r for r in pool if args.chapter in r[1] or r[1] in args.chapter]
    pool = pool[: args.n] if args.n else pool
    if not pool:
        print("[lj] 没有可复习的卡片（可加 --all 全量挑）")
        return
    for r in pool:
        print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | 下次:{r[4]}")

def _parse_due(s):
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return TODAY + dt.timedelta(days=1)

# ---------------------------------------------------------------------------
# mark —— 记录复习结果
# ---------------------------------------------------------------------------
def cmd_mark(args):
    cfg = load_config()
    rows = parse_review_lines()
    target = None
    for i, r in enumerate(rows):
        if r[0] == args.id:
            target = i
            break
    if target is None:
        fail(f"清单中找不到卡片 {args.id}")
    r = rows[target]
    stage = int(r[5]) if r[5].isdigit() else 0
    if args.result == "pass":
        stage = min(stage + 1, MAX_STAGE)
        rows[target] = review_row(r[0], r[1], r[2], "✅", add_days(INTERVALS[stage]), stage, r[6])
        msg = f"答对！进入阶段 {stage}，下次复习 {add_days(INTERVALS[stage])}"
    elif args.result == "fail":
        rows[target] = review_row(r[0], r[1], r[2], "🔄", add_days(1), 0, r[6])
        msg = "答错，重置为待复习，明天再来"
    elif args.result == "partial":
        rows[target] = review_row(r[0], r[1], r[2], "📌", add_days(2), stage, r[6])
        msg = "部分掌握，标记薄弱，后天再复习"
    else:
        fail("--result 必须是 pass / fail / partial")
    write_review_lines(rows)
    stats(cfg)
    print(f"[lj] {args.id}: {msg}")

# ---------------------------------------------------------------------------
# due —— 到期提醒（零 token，会话内提醒用）
# ---------------------------------------------------------------------------
def cmd_due(_args):
    cfg = load_config()
    rows = parse_review_lines()
    due = [r for r in rows if r[3] != "✅" and _parse_due(r[4]) <= TODAY]
    if not due:
        print("[lj] 今天没有到期卡片 🎉")
        return
    print(f"[lj] 今天有 {len(due)} 张卡片该复习了：")
    for r in due:
        print(f"  {r[0]} | {r[1]} | {r[2]}")

# ---------------------------------------------------------------------------
# archive —— 聚类归档（把待归档区卡片搬入章节）
# ---------------------------------------------------------------------------
def cmd_archive(args):
    cfg = load_config()
    if not args.json:
        fail("需要 --json '{\"K-12\":\"第四章 智能体经典范式构建\", ...}'")
    mapping = json.loads(args.json)
    note = read_note(cfg)
    # 提取待归档区卡片
    section = "待归档区"
    pos = find_chapter_pos(note, section)
    if pos is None:
        fail("笔记中没有待归档区")
    nxt = note.find("\n## ", pos + 1)
    body = note[pos:nxt if nxt != -1 else len(note)]
    rest = note[:pos] + note[nxt if nxt != -1 else len(note):]
    blocks = re.split(r"(?=^### K-\d+ )", body, flags=re.M)
    moved = 0
    for blk in blocks:
        m = re.match(r"^### (K-\d+) ", blk, re.M)
        if not m:
            continue
        cid = m.group(1)
        if cid not in mapping:
            continue
        target = mapping[cid].strip()
        if find_chapter_pos(note, target) is None:
            print(f"[lj] 跳过 {cid}：章节「{target}」在笔记中不存在", file=sys.stderr)
            continue
        rest = insert_card(rest, target, blk.strip())
        moved += 1
    cfg_note_file(cfg).write_text(rest, encoding="utf-8")
    # 更新清单中的章节名
    rows = parse_review_lines()
    for i, r in enumerate(rows):
        if r[0] in mapping:
            rows[i][1] = mapping[r[0]].strip()
    write_review_lines(rows)
    stats(cfg)
    print(f"[lj] 归档完成：搬移 {moved} 张卡片")

def cmd_complete(args):
    cfg = load_config()
    chapter = (args.chapter or "").strip()
    if not chapter:
        fail("需要 --chapter <章节名>")
    stats(cfg)
    prog = PROGRESS_FILE.read_text(encoding="utf-8") if PROGRESS_FILE.exists() else ""
    out = []
    found = False
    for line in prog.splitlines():
        if line.startswith("|") and not line.startswith("| ---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and cells[0] == chapter:
                start = cells[2] or today_str()
                out.append(f"| {chapter} | ✅ | {start} | {today_str()} | {cells[4]} | {cells[5]} |")
                found = True
                continue
        out.append(line)
    if not found:
        fail(f"进度表中找不到章节「{chapter}」")
    PROGRESS_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[lj] 已完成章节：{chapter}")

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(prog="lj.py", description="learning-journal 学习记录与复习系统")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="初始化 learning 四件套")
    p_init.add_argument("--course", default="")
    p_init.add_argument("--docs", default="")
    p_init.add_argument("--chapters", default="")
    p_init.add_argument("--open", action="store_true", help="开放式课程（不预建章节，先入待归档区）")
    p_init.add_argument("--template", default="编程", choices=["编程", "语言"])
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add", help="追加卡片（JSON: {chapter,type,title,q,a,code,point,summary,ref,lang}）")
    p_add.add_argument("card", nargs="?", default="", help="卡片 JSON（或使用 --json / stdin）")
    p_add.add_argument("--json", default="")
    p_add.set_defaults(func=cmd_add)

    p_pick = sub.add_parser("pick", help="挑复习卡片")
    p_pick.add_argument("--chapter", default="")
    p_pick.add_argument("--n", type=int, default=5)
    p_pick.add_argument("--all", action="store_true")
    p_pick.set_defaults(func=cmd_pick)

    p_mark = sub.add_parser("mark", help="记录复习结果")
    p_mark.add_argument("--id", required=True)
    p_mark.add_argument("--result", required=True, choices=["pass", "fail", "partial"])
    p_mark.set_defaults(func=cmd_mark)

    sub.add_parser("due", help="列出到期卡片").set_defaults(func=cmd_due)
    p_archive = sub.add_parser("archive", help="聚类归档")
    p_archive.add_argument("--json", required=True)
    p_archive.set_defaults(func=cmd_archive)
    p_complete = sub.add_parser("complete", help="手动完成章节")
    p_complete.add_argument("--chapter", required=True)
    p_complete.set_defaults(func=cmd_complete)
    p_stats = sub.add_parser("stats", help="刷新统计")
    p_stats.set_defaults(func=cmd_stats)

    args = p.parse_args()
    args.func(args)

def cmd_stats(args):
    counts, due = stats()
    print("[lj] 统计已刷新：")
    for ch, n in counts.items():
        print(f"  {ch}: {n} 张卡片, {due.get(ch, 0)} 张待复习")

if __name__ == "__main__":
    main()
