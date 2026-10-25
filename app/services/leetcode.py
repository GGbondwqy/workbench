# -*- coding: utf-8 -*-
"""力扣对接域（DESIGN v2.0 F15；2026-10-25 适配 leetcode.cn GraphQL 现行 schema；
v2.18 起兼本地刷题文件夹主域：问 AI（F31）+ 到期复习（F32））：

- 公开进度：用户名即可（通过数/难度分布；userSessionProgress → V2 兜底）
- 最近 AC：需要登录 Cookie（存本机 config，过期时返回明确标记；recentACSubmissions）
- 多查询模板依次尝试，适配字段变更；Cookie 失效不抛异常，返回 cookie_expired
- 本地文件夹（config leetcode.folder）：只读解析 learning/ 体系 + lj.py 子进程回写
  （该文件夹唯一写入者是 lj.py，工作台不直改 md）；纯函数可离线测，模块隔离不引 grad
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from app.core.registry import AppContext
from app.core.textkit import (  # v1.21：通用文本能力下沉 core（抽取/分块/选段）
    TEXT_EXTS,
    chunks_of as _chunks_of,
    extract_text as _extract_text,
    select_chunks as _select_chunks,
)
from app.core.timeutil import now

API = "https://leetcode.cn/graphql/"
API_GO = "https://leetcode.cn/graphql/noj-go/"   # v2：recentACSubmissions 等新查询在 Go 后端
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# v2 现行 schema（2026-10 从站点前端 JS 包提取）：难度分布为 {difficulty, count} 列表
PROGRESS_QUERIES = [
    {"query": """query userSessionProgress($userSlug: String!) {
        userProfileUserQuestionSubmitStats(userSlug: $userSlug) {
            acSubmissionNum { difficulty count }
            totalSubmissionNum { difficulty count }
        } userProfileUserQuestionProgress(userSlug: $userSlug) {
            numAcceptedQuestions { difficulty count }
            numFailedQuestions { difficulty count }
            numUntouchedQuestions { difficulty count }
        } }"""},
    {"query": """query userProfileUserQuestionProgressV2($userSlug: String!) {
        userProfileUserQuestionProgressV2(userSlug: $userSlug) {
            numAcceptedQuestions { difficulty count }
            numFailedQuestions { difficulty count }
            numUntouchedQuestions { difficulty count }
        } }"""},
]

RECENT_QUERY = """query recentAcSubmissions($userSlug: String!) {
    recentACSubmissions(userSlug: $userSlug) {
        submissionId
        submitTime
        question { title translatedTitle titleSlug questionFrontendId }
    } }"""


def _gql(query, variables, cookie=None, endpoint=API):
    req = Request(endpoint, data=json.dumps({"query": query, "variables": variables}).encode(),
                  headers={"Content-Type": "application/json",
                           "Referer": "https://leetcode.cn/",
                           "User-Agent": _UA,
                           **({"Cookie": cookie} if cookie else {})},
                  method="POST")
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    else:
        out[prefix] = d
    return out


def _counts_by_difficulty(rows) -> dict:
    """[{difficulty, count}] → {easy: n, medium: n, hard: n}（同难度重复行累加）。"""
    out = {}
    for r in rows or []:
        if isinstance(r, dict) and r.get("difficulty"):
            k = str(r["difficulty"]).lower()
            out[k] = out.get(k, 0) + int(r.get("count") or 0)
    return out


def _first_rows(data: dict, *paths):
    """按优先级取第一个非空的嵌套路径值（同份数据在两种 schema 下的不同形态，取一即可）。"""
    for src in paths:
        rows = data
        for part in src.split("."):
            rows = rows.get(part) if isinstance(rows, dict) else None
            if rows is None:
                break
        if rows:
            return rows
    return None


def _progress_of(data: dict) -> dict:
    """GraphQL data → 展示用进度 dict；解析不出返回 {}。

    兼容两路 schema：userSessionProgress（submit stats + progress）与 V2——
    难度分布各来源互为同一数据的别名，按优先级取第一个非空，不叠加。"""
    if not isinstance(data, dict) or not data:
        return {}
    ac = _counts_by_difficulty(_first_rows(
        data, "userProfileUserQuestionSubmitStats.acSubmissionNum",
        "userProfileUserQuestionProgress.numAcceptedQuestions",
        "userProfileUserQuestionProgressV2.numAcceptedQuestions"))
    if not ac:
        return {}
    failed = _counts_by_difficulty(_first_rows(
        data, "userProfileUserQuestionProgress.numFailedQuestions",
        "userProfileUserQuestionProgressV2.numFailedQuestions"))
    untouched = _counts_by_difficulty(_first_rows(
        data, "userProfileUserQuestionProgress.numUntouchedQuestions",
        "userProfileUserQuestionProgressV2.numUntouchedQuestions"))
    total = ac.get("easy", 0) + ac.get("medium", 0) + ac.get("hard", 0)
    out = {"solved": total, "easy": ac.get("easy", 0),
           "medium": ac.get("medium", 0), "hard": ac.get("hard", 0)}
    if failed or untouched:
        out["attempted"] = sum(failed.values())
        out["untouched"] = sum(untouched.values())
    return out


def _recent_rows(recent: list):
    """recentACSubmissions 结果 → [(day, title, difficulty)]（ difficulty 新 schema 已无，空串）。"""
    rows = []
    for sub in recent or []:
        q = sub.get("question") or {}
        title = q.get("translatedTitle") or q.get("title") or q.get("titleSlug") or "未知名题目"
        ts = int(sub.get("submitTime") or sub.get("timestamp") or 0)
        day = date.fromtimestamp(ts).isoformat() if ts else None
        rows.append((day, title, ""))
    return rows


# ---- v2.18 本地刷题文件夹（F31/F32）：域内纯函数（卡片解析/清单解析/lj 输出解析）；
#      通用抽取/分块/选段已下沉 core/textkit（v1.21 共享，services 向下 import 合法） ----
_CONTEXT_BUDGET = 6000    # 单次问答喂给 AI 的资料字数预算
_ASK_K = 8                # 问 AI 最多选段数
_SCAN_CAP = 60            # 文件夹扫描文件数上限
_SKIP_DIRS = {"__pycache__", ".zcode", ".agents", ".git", "scripts", ".idea", ".vscode"}

_CARD_RE = re.compile(r"^###\s+(K-\d+)\s*(.*)$")
_H2_RE = re.compile(r"^##(?!#)\s*(.*)$")


def _iter_files(folder: Path):
    """顶层 + learning/ 一层，跳过脚本目录与隐藏目录，限 _SCAN_CAP 个。"""
    out = []
    for base in (folder, folder / "learning"):
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if not p.is_file() or p.name.startswith(".") or p.suffix.lower() not in TEXT_EXTS:
                continue
            out.append(p)
            if len(out) >= _SCAN_CAP:
                return out
    return out


def _cards_of(note_text: str) -> dict:
    """学习笔记.md → {K-N: {id, chapter, title, body}}（### K-N 起，下个 ###/## 止）。"""
    cards, chapter, cur = {}, "", None

    def flush():
        nonlocal cur
        if cur and cur["body"].strip():
            cards[cur["id"]] = cur
        cur = None

    for line in note_text.splitlines():
        m = _CARD_RE.match(line)
        if m:
            flush()
            cur = {"id": m.group(1), "chapter": chapter, "title": m.group(2).strip(), "body": ""}
            continue
        m = _H2_RE.match(line)
        if m:
            flush()
            chapter = m.group(1).strip()
            continue
        if cur is not None:
            cur["body"] += line + "\n"
    flush()
    return cards


def _field_of(body: str, name: str) -> str:
    """卡片正文里取 `- **问**：` 式字段值（到下一个字段/卡片头为止）。"""
    m = re.search(rf"\*\*{name}\*\*[：:]\s*(.+?)(?=\n\s*-\s*\*\*|\n###|\Z)", body, re.S)
    return m.group(1).strip() if m else ""


def _due_count(review_text: str) -> int:
    """复习清单.md 表格行 → 今日到期数（状态非 ✅ 且 下次复习 <= 今天）。"""
    today = date.today()
    n = 0
    for line in review_text.splitlines():
        s = line.strip()
        if not s.startswith("|") or set(s) <= {"|", "-", " ", ":"}:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 5 or not re.match(r"^[A-Z]-\d+$", cells[0]):
            continue
        if cells[3] == "✅":
            continue
        try:
            if date.fromisoformat(cells[4]) <= today:
                n += 1
        except ValueError:
            continue
    return n


def _parse_pick_rows(out: str):
    """lj.py pick 输出 → [{id, chapter, title, status, due}]（标题含 | 时按首尾字段定位）。"""
    rows = []
    for line in (out or "").splitlines():
        if "|" not in line or line.strip().startswith("[lj]"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4 or not re.match(r"^K-\d+$", parts[0]):
            continue
        due = parts[-1].replace("下次:", "").strip() if parts[-1].startswith("下次:") else ""
        status = parts[-2] if due else parts[-1]
        title = "|".join(parts[2:-2]) if due else "|".join(parts[2:-1])
        rows.append({"id": parts[0], "chapter": parts[1], "title": title,
                     "status": status, "due": due})
    return rows


def _lj_msg(out: str) -> str:
    m = re.search(r"\[lj\]\s*(.+)", out or "")
    return m.group(1).strip() if m else (out or "").strip()


class LeetcodeService:
    name = "leetcode_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def _cfg(self):
        return self._ctx.config.get("leetcode", {})

    def configured(self):
        return bool(self._cfg().get("username"))

    def sync(self):
        """同步进度与最近 AC；最近 AC 去重写入刷题记录。"""
        cfg = self._cfg()
        user = cfg.get("username")
        if not user:
            return {"error": "未配置力扣用户名（设置页填写）"}
        cookie = cfg.get("cookie", "")
        progress = {}
        for q in PROGRESS_QUERIES:
            try:
                data = _gql(q["query"], {"userSlug": user})
                progress = _progress_of(data.get("data") or {})
                if progress:
                    break
            except Exception:
                continue
        if not progress:
            return {"error": "拉取进度失败（用户名可能不存在或接口变更）"}

        recent, cookie_ok = [], True
        try:
            data = _gql(RECENT_QUERY, {"userSlug": user}, cookie=cookie or None, endpoint=API_GO)
            recent = (data.get("data") or {}).get("recentACSubmissions") or []
            cookie_ok = not data.get("errors")
        except Exception:
            cookie_ok = False

        imported = self._import_recent(recent) if recent else 0
        result = {
            "user": user, "progress": progress, "recent_imported": imported,
            "cookie_ok": cookie_ok, "synced_at": now(),
        }
        self._ctx.services.get("settings_service").set("leetcode_cache", result)
        if not cookie_ok:
            result["notice"] = "Cookie 缺失或过期：最近提交未同步，请在设置页更新 Cookie"
        return result

    def _import_recent(self, recent):
        career = self._ctx.services.get("career_service")
        n = 0
        for day, title, diff in _recent_rows(recent):
            # 去重：同日同题不重复写（借刷题记录查询判断）
            exists = self._ctx.db.query_one(
                "SELECT 1 FROM career_problems WHERE date=? AND title=?", (day, title))
            if exists:
                continue
            career.add_problem(day=day, title=title, difficulty=diff,
                               topic="力扣同步", minutes=0, note="leetcode.cn 自动同步")
            n += 1
        return n

    def cached(self):
        return self._ctx.services.get("settings_service").get("leetcode_cache")

    # ---- v2.18 本地刷题文件夹（F31 问 AI / F32 到期复习） ----

    def folder_path(self) -> str:
        return str(self._cfg().get("folder") or "").strip()

    def folder_status(self) -> dict:
        """绑定文件夹的健康状况（只读解析，不触发 lj.py）。"""
        path = self.folder_path()
        out = {"bound": bool(path), "path": path, "exists": False,
               "has_learning": False, "cards": 0, "chapters": 0, "due": 0, "files": 0}
        if not path:
            return out
        folder = Path(path)
        if not folder.is_dir():
            return out
        out["exists"] = True
        out["files"] = len(_iter_files(folder))
        note, review = folder / "learning" / "学习笔记.md", folder / "learning" / "复习清单.md"
        if note.is_file():
            cards = _cards_of(note.read_text(encoding="utf-8", errors="ignore"))
            out["has_learning"] = True
            out["cards"] = len(cards)
            out["chapters"] = len({c["chapter"] for c in cards.values() if c["chapter"]})
        if review.is_file():
            out["due"] = _due_count(review.read_text(encoding="utf-8", errors="ignore"))
        return out

    def ask(self, question: str) -> dict:
        """F31 力扣问 AI：本地文件夹资料选段 → AI 作答（降级=相关段落）。"""
        q = (question or "").strip()
        if not q:
            raise ValueError("问题不能为空")
        if not self.folder_path():
            return {"answer": "还没绑定本地刷题文件夹：在本页「📚 本地刷题文件夹」或设置页填路径"
                              "（例如 D:\\leetcode）后即可基于学习笔记提问。",
                    "sources": [], "ai_used": False}
        files = []
        for p in _iter_files(Path(self.folder_path())):
            text = _extract_text(p)
            if text:
                cs = _chunks_of(text)
                if cs:
                    files.append((p.name, cs))
        chunks = _select_chunks(files, q, k=_ASK_K, budget=_CONTEXT_BUDGET)
        context = "\n\n".join(f"《{x['name']}》片段：\n{x['text']}" for x in chunks)
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是算法刷题辅导助手。优先依据给定的学习笔记/资料片段回答，并标注来源（卡片编号如 K-3 或文件名）；"
                "资料不足以完整回答时可用你自己的可靠知识补充，补充部分标注'（补充）'；"
                "与算法刷题无关的问题直接说明。用简洁中文回答。"},
            {"role": "user", "content": f"问题：{q}\n\n本地资料片段：\n{context or '（无可读文本资料）'}"},
        ], feature="力扣问答")
        names, card_ids = [], []
        for x in chunks:
            if x["name"] not in names:
                names.append(x["name"])
            for m in re.findall(r"\bK-\d+\b", x["text"]):
                if m not in card_ids:
                    card_ids.append(m)
        sources = [{"name": n} for n in names] + [{"card": c} for c in card_ids[:6]]
        if ai:
            return {"answer": ai.strip(), "sources": sources, "ai_used": True}
        if chunks:
            ref = "（AI 未配置——以下是学习笔记中最相关的段落，供参考）\n\n" + "\n\n".join(
                f"**《{x['name']}》**：{x['text'][:200]}…" for x in chunks[:4])
        else:
            ref = "绑定的文件夹里没有可读的文本资料（md/txt/代码文件），且当前未接 AI。"
        return {"answer": ref, "sources": sources, "ai_used": False}

    def _lj_path(self):
        if not self.folder_path():
            return None
        p = Path(self.folder_path()) / "learning" / "scripts" / "lj.py"
        return p if p.is_file() else None

    def _lj_run(self, *args, timeout=30):
        lj = self._lj_path()
        if not lj:
            return None, "绑定的文件夹里没有 learning/scripts/lj.py（学习助手体系），复习打卡不可用"
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", str(lj), *args],
                               capture_output=True, timeout=timeout,
                               encoding="utf-8", errors="ignore")
        except subprocess.TimeoutExpired:
            return None, "lj.py 执行超时"
        if r.returncode != 0:
            return None, (r.stderr or r.stdout or "lj.py 执行失败").strip()[:200]
        return (r.stdout or "").strip(), None

    def review_pick(self, n=5) -> dict:
        """F32：lj.py pick 挑到期卡（到期优先，兜底 🔄/📌/⬜ 池），附卡片正文。"""
        try:
            n = max(1, min(int(n or 5), 10))
        except (TypeError, ValueError):
            n = 5
        out, err = self._lj_run("pick", "--n", str(n))
        if err:
            raise ValueError(err)
        rows = _parse_pick_rows(out)
        if not rows:
            return {"cards": [], "msg": _lj_msg(out) or "没有可复习的卡片"}
        cards_map = {}
        note = Path(self.folder_path()) / "learning" / "学习笔记.md"
        if note.is_file():
            cards_map = _cards_of(note.read_text(encoding="utf-8", errors="ignore"))
        cards = []
        for r in rows:
            body = cards_map.get(r["id"], {}).get("body", "")
            cards.append({**r, "q": _field_of(body, "问") or r["title"],
                          "a": _field_of(body, "答"),
                          "ref": body.strip()[:1200] or r["title"]})
        return {"cards": cards, "msg": ""}

    def review_grade(self, question: str, answer: str, ref: str = "") -> dict:
        """复习判分（与课程 AI 考我同形态；ref=卡片正文）。"""
        if not (question or "").strip() or not (answer or "").strip():
            raise ValueError("题目与作答不能为空")
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是严格的算法面试官，根据参考要点评判学生答案。"
                "第一行只输出三个词之一：过 / 含糊 / 没过；第二行给一句不超过50字的点评。"},
            {"role": "user", "content":
                f"题目：{question}\n参考要点：{ref or '（无）'}\n学生作答：{answer}"},
        ], feature="力扣复习")
        if not ai:
            return {"verdict": None, "comment": "（AI 未配置——对照卡片要点自评）", "ai_used": False}
        lines = [l.strip() for l in ai.strip().splitlines() if l.strip()]
        first = lines[0] if lines else ""
        verdict = ("fail" if "没" in first else
                   "fuzzy" if "含糊" in first or "部分" in first else
                   "pass" if "过" in first else None)
        return {"verdict": verdict, "comment": " ".join(lines[1:]) or "", "ai_used": True}

    def review_mark(self, cid: str, result: str) -> dict:
        """复习结果回写记忆曲线：pass 进阶段 / fail 重置 / partial 标薄弱（lj.py 唯一写入者）。"""
        if result not in ("pass", "fail", "partial"):
            raise ValueError("result 必须是 pass/fail/partial")
        if not re.match(r"^K-\d+$", str(cid or "")):
            raise ValueError("卡片 ID 不合法")
        out, err = self._lj_run("mark", "--id", str(cid), "--result", result)
        if err:
            raise ValueError(err)
        return {"ok": True, "msg": _lj_msg(out) or "已记录"}


def register(ctx: AppContext):
    ctx.services.register(LeetcodeService.name, LeetcodeService(ctx))
