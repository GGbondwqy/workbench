# -*- coding: utf-8 -*-
"""研究生域：课程（→固定日程块）、组会、导师任务池（DESIGN 对象8/9，流程 F8），
v2.4 课程详情化：绑定文件夹/零散文件/复习标记/作业（F23、F24）。
v2.15 课程复习升级：F27 课程 AI 问答 / F28 AI 考我（课程资料文本按需抽取+缓存）/
F29 学习助手进驻课程文件夹（模板 _learning_skill，仅主动学习才启用）。

跨域联动（符合隔离规则）：
- 新课程（有固定时间）→ 调 schedule_service.add_fixed 生成固定块（注册表查询）
- 导师任务/作业转化 → 调 task_service.create 建任务（注册表查询）
"""
import html
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date as _date
from pathlib import Path

from app.core.registry import AppContext
from app.core.textkit import (  # v1.21：共享文本能力下沉 core（抽取/分块/选段/出题解析）
    chunks_of as _chunks_of,
    extract_text as _extract_text,
    parse_quiz_json as _parse_quiz_json,
    select_chunks as _select_chunks,
)
from app.core.timeutil import today

LOG = logging.getLogger("workbench.grad")

MIGRATIONS = [
    ("0008_grad", """
        CREATE TABLE IF NOT EXISTS grad_courses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,      -- 0=周一..6=周日；-1=无固定时间
            start_time TEXT NOT NULL,
            end_time   TEXT NOT NULL,
            place      TEXT DEFAULT '',
            weeks      TEXT DEFAULT ''          -- 备注：周次范围
        );
        CREATE TABLE IF NOT EXISTS grad_meetings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            meet_date  TEXT NOT NULL,
            title      TEXT DEFAULT '',
            notes      TEXT DEFAULT '',         -- 会议纪要
            my_todos   TEXT DEFAULT ''          -- 我的待办（文本）
        );
        CREATE TABLE IF NOT EXISTS grad_advisor_tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            content      TEXT NOT NULL,
            created_date TEXT NOT NULL,
            status       TEXT DEFAULT 'pending', -- pending/converted/ignored
            task_id      INTEGER
        );
    """),
    ("0009_grad_course_detail", """
        ALTER TABLE grad_courses ADD COLUMN folder_path TEXT NOT NULL DEFAULT '';
        ALTER TABLE grad_courses ADD COLUMN schedule_block_id INTEGER;
        CREATE TABLE IF NOT EXISTS grad_course_files (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id   INTEGER NOT NULL,
            name        TEXT NOT NULL,
            path        TEXT NOT NULL,           -- 本机完整路径（零散文件登记）
            added_date  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS grad_file_reviews (
            course_id     INTEGER NOT NULL,
            file_key      TEXT NOT NULL,          -- 文件完整路径（文件夹内文件动态扫描，不入库）
            reviewed_date TEXT NOT NULL,
            PRIMARY KEY (course_id, file_key)
        );
        CREATE TABLE IF NOT EXISTS grad_assignments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id   INTEGER NOT NULL,
            title       TEXT NOT NULL,
            due_date    TEXT DEFAULT '',          -- YYYY-MM-DD，空=无截止
            status      TEXT DEFAULT 'todo',      -- todo/done
            note        TEXT DEFAULT '',
            file_ref    TEXT DEFAULT '',          -- 关联课程文件路径（可空）
            converted_task_id INTEGER,            -- 转今日待办后回填，防重复转
            created_date TEXT NOT NULL
        );
    """),
    ("0025_grad_course_ai", """
        CREATE TABLE IF NOT EXISTS grad_file_text (   -- F27：课程资料文本按需抽取缓存
            course_id INTEGER NOT NULL,
            file_key  TEXT NOT NULL,              -- 文件完整路径
            mtime     REAL NOT NULL,              -- 抽取时的文件修改时间
            text      TEXT NOT NULL,
            PRIMARY KEY (course_id, file_key)
        );
    """),
]

_FOLDER_SCAN_CAP = 500  # 文件夹动态扫描上限，防误绑大目录拖垮详情页

# ---- v2.15 课程资料文本能力（F27/F28）：实现已下沉 core/textkit，此处只留域内编排 ----
_CONTEXT_BUDGET = 6000    # 单次问答喂给 AI 的资料字数预算

_SKILL_NAME = "learning-assistant"
_SKILL_TEMPLATE = Path(__file__).resolve().parent / "_learning_skill"


class GradService:
    name = "grad_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 课程 ----
    def add_course(self, name, day_of_week=None, start_time="", end_time="",
                   place="", weeks="", folder_path=""):
        """v2.4：上课时间选填。day_of_week 为 None/-1 表示无固定时间，不生成日程块。
        v2.5：建课即可一步绑文件夹（路径校验同换绑）。"""
        day = -1 if day_of_week is None else int(day_of_week)
        folder = ""
        if folder_path and folder_path.strip():
            folder = str(Path(folder_path).resolve())
            if not Path(folder).is_dir():
                raise ValueError("文件夹不存在：" + folder_path)
        sched_id = None
        if 0 <= day <= 6 and start_time and end_time:
            block = self._ctx.services.get("schedule_service").add_fixed(
                title=name, day_of_week=day,
                start_time=start_time, end_time=end_time, place=place)
            sched_id = block["id"]
        cid = self._ctx.db.execute(
            "INSERT INTO grad_courses (name, day_of_week, start_time, end_time, place, weeks,"
            " folder_path, schedule_block_id) VALUES (?,?,?,?,?,?,?,?)",
            (name, day, start_time or "", end_time or "", place, weeks,
             folder, sched_id))
        if folder:  # v2.15 F29：建课即自动进驻学习助手（失败不阻塞建课）
            try:
                self.install_skill(cid)
            except Exception as e:
                LOG.warning("课程 %s 学习助手自动安装失败：%s", name, e)
        return cid

    def courses(self):
        rows = self._ctx.db.query(
            "SELECT * FROM grad_courses"
            " ORDER BY (day_of_week < 0), day_of_week, start_time")
        open_a = {r["course_id"]: r["n"] for r in self._ctx.db.query(
            "SELECT course_id, COUNT(*) n FROM grad_assignments"
            " WHERE status='todo' GROUP BY course_id")}
        loose = {r["course_id"]: r["n"] for r in self._ctx.db.query(
            "SELECT course_id, COUNT(*) n FROM grad_course_files GROUP BY course_id")}
        for c in rows:
            c["open_assignments"] = open_a.get(c["id"], 0)
            c["file_count"] = loose.get(c["id"], 0) + self._folder_file_count(c["folder_path"])
            c["has_schedule"] = 0 <= c["day_of_week"] <= 6
        return rows

    def get_course(self, cid):
        return self._ctx.db.query_one("SELECT * FROM grad_courses WHERE id=?", (cid,))

    def update_course(self, cid, name=None, folder_path=None, day_of_week=None,
                      start_time=None, end_time=None, place=None, weeks=None):
        c = self.get_course(cid)
        if not c:
            return None
        sets, args = [], []
        if name is not None:
            sets.append("name=?"); args.append(name)
        if place is not None:
            sets.append("place=?"); args.append(place)
        if weeks is not None:
            sets.append("weeks=?"); args.append(weeks)
        if folder_path is not None:
            path = str(Path(folder_path).resolve()) if folder_path.strip() else ""
            if path and not Path(path).is_dir():
                raise ValueError("文件夹不存在：" + folder_path)
            sets.append("folder_path=?"); args.append(path)
        # 上课时间：传入 day_of_week 才视为要改时间（-1=改为无固定时间）
        if day_of_week is not None:
            day = int(day_of_week)
            st = start_time if start_time is not None else c["start_time"]
            et = end_time if end_time is not None else c["end_time"]
            sets += ["day_of_week=?", "start_time=?", "end_time=?"]
            args += [day, st or "", et or ""]
            self._sync_schedule_block(c, day, st or "", et or "",
                                      place if place is not None else c["place"],
                                      name if name is not None else c["name"])
        if sets:
            args.append(cid)
            self._ctx.db.execute(f"UPDATE grad_courses SET {', '.join(sets)} WHERE id=?", args)
        updated = self.get_course(cid)
        # v2.15 F29：换绑到新的非空文件夹 → 自动进驻学习助手（失败不阻塞换绑）
        if (folder_path is not None and updated["folder_path"]
                and updated["folder_path"] != (c["folder_path"] or "")
                and not self.skill_installed(updated)):
            try:
                self.install_skill(cid)
            except Exception as e:
                LOG.warning("课程 %s 学习助手自动安装失败：%s", updated["name"], e)
        return self.get_course(cid)

    def _sync_schedule_block(self, course, day, start_time, end_time, place, name):
        """课程时间变更 → 重建固定日程块（旧块删除、新块回填 id；无时间则只删）。"""
        sched = self._ctx.services.get("schedule_service")
        if course["schedule_block_id"]:
            sched.delete_block(course["schedule_block_id"])
        else:  # 存量课（0009 前建）无 id，按特征匹配清理一个（重名课场景只删自己的块）
            for b in sched.fixed_blocks():
                if (b["title"] == course["name"] and b["day_of_week"] == course["day_of_week"]
                        and b["start_time"] == course["start_time"]):
                    sched.delete_block(b["id"])
                    break
        new_id = None
        if 0 <= day <= 6 and start_time and end_time:
            new_id = sched.add_fixed(title=name, day_of_week=day,
                                     start_time=start_time, end_time=end_time,
                                     place=place)["id"]
        self._ctx.db.execute(
            "UPDATE grad_courses SET schedule_block_id=? WHERE id=?", (new_id, course["id"]))

    def delete_course(self, cid):
        c = self.get_course(cid)
        if not c:
            return
        sched = self._ctx.services.get("schedule_service")
        if c["schedule_block_id"]:
            sched.delete_block(c["schedule_block_id"])
        else:  # 存量课无 id：按特征匹配清理一个，避免孤儿块
            for b in sched.fixed_blocks():
                if (b["title"] == c["name"] and b["day_of_week"] == c["day_of_week"]
                        and b["start_time"] == c["start_time"]):
                    sched.delete_block(b["id"])
                    break
        for t in ("grad_assignments", "grad_course_files", "grad_file_reviews",
                  "grad_file_text"):
            self._ctx.db.execute(f"DELETE FROM {t} WHERE course_id=?", (cid,))
        self._ctx.db.execute("DELETE FROM grad_courses WHERE id=?", (cid,))

    # ---- 课程详情：文件夹扫描 + 零散文件 + 复习标记（F23） ----
    def course_detail(self, cid):
        c = self.get_course(cid)
        if not c:
            return None
        c["has_schedule"] = 0 <= c["day_of_week"] <= 6
        c["skill_installed"] = self.skill_installed(c)
        files = self._files_of(c)
        assignments = []
        for a in self._ctx.db.query(
                "SELECT * FROM grad_assignments WHERE course_id=?"
                " ORDER BY (due_date=''), due_date, id", (cid,)):
            a["days_left"] = self._days_left(a["due_date"]) if a["due_date"] else None
            assignments.append(a)
        reviewed = sum(1 for f in files if f["reviewed"])
        return {
            "course": c,
            "files": files,
            "review_progress": {"reviewed": reviewed, "total": len(files)},
            "assignments": assignments,
            "open_assignments": sum(1 for a in assignments if a["status"] == "todo"),
        }

    def _files_of(self, course):
        reviews = {r["file_key"]: r["reviewed_date"] for r in self._ctx.db.query(
            "SELECT * FROM grad_file_reviews WHERE course_id=?", (course["id"],))}
        files = []
        folder = course["folder_path"]
        if folder and Path(folder).is_dir():
            entries = sorted(Path(folder).iterdir(), key=lambda p: p.name.lower())
            for p in entries[:_FOLDER_SCAN_CAP]:
                if not p.is_file() or p.name.startswith("~$") or p.name.startswith("."):
                    continue
                try:
                    size = p.stat().st_size
                except OSError:
                    size = None
                files.append({"name": p.name, "path": str(p), "size": size,
                              "loose": False, "file_id": None,
                              "exists": True,
                              "reviewed": str(p) in reviews,
                              "reviewed_date": reviews.get(str(p), "")})
        for f in self._ctx.db.query(
                "SELECT * FROM grad_course_files WHERE course_id=? ORDER BY id", (course["id"],)):
            exists = Path(f["path"]).is_file()
            files.append({"name": f["name"], "path": f["path"],
                          "size": None, "loose": True, "file_id": f["id"],
                          "exists": exists,
                          "reviewed": f["path"] in reviews,
                          "reviewed_date": reviews.get(f["path"], "")})
        return files

    def _folder_file_count(self, folder):
        if not folder or not Path(folder).is_dir():
            return 0
        n = 0
        for p in Path(folder).iterdir():
            if p.is_file() and not p.name.startswith("~$") and not p.name.startswith("."):
                n += 1
        return n

    def _file_allowed(self, course, path):
        """路径归属校验：在绑定文件夹内，或为本课程零散登记文件。"""
        folder = course["folder_path"]
        if folder:
            try:
                if Path(path).resolve().is_relative_to(Path(folder).resolve()):
                    return True
            except (OSError, ValueError):
                pass
        row = self._ctx.db.query_one(
            "SELECT id FROM grad_course_files WHERE course_id=? AND path=?",
            (course["id"], path))
        return row is not None

    def add_file(self, cid, path, name=""):
        """登记零散文件（不在绑定文件夹里的）。"""
        c = self.get_course(cid)
        if not c:
            raise ValueError("课程不存在")
        p = Path(path)
        if not p.is_file():
            raise ValueError("文件不存在：" + path)
        fid = self._ctx.db.execute(
            "INSERT INTO grad_course_files (course_id, name, path, added_date) VALUES (?,?,?,?)",
            (cid, name.strip() or p.name, str(p.resolve()), today()))
        return fid

    def delete_file(self, cid, fid):
        row = self._ctx.db.query_one(
            "SELECT * FROM grad_course_files WHERE id=? AND course_id=?", (fid, cid))
        if not row:
            return
        self._ctx.db.execute("DELETE FROM grad_course_files WHERE id=?", (fid,))
        self._ctx.db.execute(
            "DELETE FROM grad_file_reviews WHERE course_id=? AND file_key=?",
            (cid, row["path"]))

    def open_file(self, cid, path):
        """用系统默认程序打开课程文件（F23）。"""
        c = self.get_course(cid)
        if not c:
            raise ValueError("课程不存在")
        if not self._file_allowed(c, path):
            raise ValueError("该文件不属于这门课（不在绑定文件夹内，也不是登记的零散文件）")
        if not Path(path).is_file():
            raise ValueError("文件不存在（可能已被移动或删除）")
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 本地单机工具，属预期行为
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def set_file_review(self, cid, path, reviewed):
        c = self.get_course(cid)
        if not c:
            raise ValueError("课程不存在")
        if not self._file_allowed(c, path):
            raise ValueError("该文件不属于这门课")
        if reviewed:
            self._ctx.db.execute(
                "INSERT OR REPLACE INTO grad_file_reviews (course_id, file_key, reviewed_date)"
                " VALUES (?,?,?)", (cid, path, today()))
        else:
            self._ctx.db.execute(
                "DELETE FROM grad_file_reviews WHERE course_id=? AND file_key=?", (cid, path))

    # ---- 学习助手进驻课程文件夹（F29，v2.15） ----
    def skill_installed(self, course) -> bool:
        folder = course["folder_path"] if course else ""
        return bool(folder) and (Path(folder) / ".zcode" / "skills" / _SKILL_NAME
                                 / "SKILL.md").is_file()

    def install_skill(self, cid, force=True):
        """把学习助手模板装进课程文件夹：SKILL.md 双落点（.zcode/.agents）+ lj.py + learning/ 日志。
        SKILL.md/lj.py 属软件托管文件可覆盖刷新；learning/*.md 是用户笔记，已初始化则绝不覆盖。"""
        c = self.get_course(cid)
        if not c:
            raise ValueError("课程不存在")
        folder = c["folder_path"]
        if not folder or not Path(folder).is_dir():
            raise ValueError("课程未绑定有效文件夹，无法安装学习助手")
        root = Path(folder)
        if not (_SKILL_TEMPLATE / "SKILL.md").is_file():
            raise ValueError("学习助手模板缺失（_learning_skill）")
        skill_files = []
        for base in (".zcode", ".agents"):
            d = root / base / "skills" / _SKILL_NAME
            d.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_SKILL_TEMPLATE / "SKILL.md", d / "SKILL.md")
            skill_files.append(str((d / "SKILL.md").resolve()))
        scripts = root / "learning" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_SKILL_TEMPLATE / "lj.py", scripts / "lj.py")
        inited = False
        if not (root / "learning" / "学习配置.md").exists():
            r = subprocess.run(
                [sys.executable, str(scripts / "lj.py"), "init", "--course", c["name"], "--open"],
                capture_output=True, text=True, encoding="utf-8", errors="ignore",
                timeout=60, cwd=str(root))
            if r.returncode != 0:
                raise ValueError("学习目录初始化失败："
                                 + ((r.stderr or r.stdout or "").strip()[-200:] or "未知错误"))
            inited = True
        return {"installed": True, "inited": inited, "skill_files": skill_files}

    # ---- 课程 AI 问答 / AI 考我（F27/F28，v2.15） ----
    def _file_text(self, cid, path):
        """按需抽取 + mtime 缓存；空文本不缓存（装上 pypdf 后 PDF 自动可用）。"""
        try:
            mtime = Path(path).stat().st_mtime
        except OSError:
            return ""
        row = self._ctx.db.query_one(
            "SELECT mtime, text FROM grad_file_text WHERE course_id=? AND file_key=?",
            (cid, path))
        if row and abs((row["mtime"] or 0) - mtime) < 1:
            return row["text"]
        text = _extract_text(Path(path))
        if text:
            self._ctx.db.execute(
                "INSERT OR REPLACE INTO grad_file_text (course_id, file_key, mtime, text)"
                " VALUES (?,?,?,?)", (cid, path, mtime, text))
        return text

    def _course_context(self, course, query, k=8):
        """收集课程文件（文件夹+零散）→ 抽文本 → 分块 → 选段（textkit.select_chunks）。
        query 为空时轮转各文件取段（出题用，保证文件间均衡）。"""
        files_text = []
        for f in self._files_of(course):
            if not f["exists"]:
                continue
            text = self._file_text(course["id"], f["path"])
            if not text:
                continue
            cs = _chunks_of(text)
            if cs:
                files_text.append((f["name"], cs))
        return _select_chunks(files_text, query, k=k, budget=_CONTEXT_BUDGET)

    def course_ask(self, cid, question):
        c = self.get_course(cid)
        if not c:
            raise ValueError("课程不存在")
        q = (question or "").strip()
        if not q:
            raise ValueError("问题不能为空")
        chunks = self._course_context(c, q)
        context = "\n\n".join(f"《{x['name']}》片段：\n{x['text']}" for x in chunks)
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是研究生课程复习辅导助手。优先依据给定的课程资料片段回答，并标注来源文件名；"
                "资料不足以完整回答时可用你自己的可靠知识补充，补充部分标注'（补充）'；"
                "与该课程无关的问题直接说明。用简洁中文回答。"},
            {"role": "user", "content":
                f"课程：{c['name']}\n问题：{q}\n\n课程资料片段：\n{context or '（无可读文本资料）'}"},
        ], feature="课程问答")
        names = []
        for x in chunks:
            if x["name"] not in names:
                names.append(x["name"])
        sources = [{"name": n} for n in names]
        if ai:
            return {"answer": ai.strip(), "sources": sources, "ai_used": True}
        if chunks:
            ref = "（AI 未配置——以下是课程资料中最相关的段落，供参考）\n\n" + "\n\n".join(
                f"**《{x['name']}》**：{x['text'][:200]}…" for x in chunks[:4])
        else:
            ref = ("课程文件夹里没有可读的文本资料（PPT/Word 演示文稿会自动解析，"
                   "PDF 需要可选组件 pypdf：pip install pypdf），且当前未接 AI。")
        return {"answer": ref, "sources": sources, "ai_used": False}

    def course_quiz(self, cid, n=5):
        c = self.get_course(cid)
        if not c:
            raise ValueError("课程不存在")
        try:
            n = max(1, min(int(n or 5), 10))
        except (TypeError, ValueError):
            n = 5
        chunks = self._course_context(c, "", k=max(n, 5))
        if not chunks:
            raise ValueError("课程文件夹里没有可读的文本资料，无法出题"
                             "（PPT/Word 自动解析，PDF 需要可选组件 pypdf）")
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是研究生课程助教。基于课程资料出 n 道期末复习简答题，覆盖不同知识点、"
                "由浅入深。只输出 JSON 数组，格式 [{\"q\": \"问题\"}, …]，不要输出其他内容。"},
            {"role": "user", "content":
                f"课程：{c['name']}\n出题数量：{n}\n\n课程资料片段：\n"
                + "\n\n".join(f"《{x['name']}》：{x['text']}" for x in chunks)},
        ], feature="课程问答")
        questions = _parse_quiz_json(ai or "", n)
        ai_used = bool(questions)
        if not questions:  # 降级：资料片段复述自测
            questions = [{"q": f"自测·复述：下面这段《{x['name']}》的资料讲了什么？要点有哪些？",
                          "ref": x["text"][:600]} for x in chunks[:n]]
        return {"questions": questions, "ai_used": ai_used}

    def course_quiz_grade(self, cid, question, answer, ref=""):
        if not self.get_course(cid):
            raise ValueError("课程不存在")
        if not (question or "").strip() or not (answer or "").strip():
            raise ValueError("题目与作答不能为空")
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是严格的课程助教，根据参考要点评判学生答案。"
                "第一行只输出三个词之一：过 / 含糊 / 没过；第二行给一句不超过50字的点评。"},
            {"role": "user", "content":
                f"题目：{question}\n参考要点：{ref or '（无）'}\n学生作答：{answer}"},
        ], feature="课程问答")
        if not ai:
            return {"verdict": None, "comment": "（AI 未配置——请对照参考要点自评）",
                    "ai_used": False}
        lines = [l.strip() for l in ai.strip().splitlines() if l.strip()]
        first = lines[0] if lines else ""
        verdict = ("fail" if "没" in first else
                   "fuzzy" if "含糊" in first or "部分" in first else
                   "pass" if "过" in first else None)
        return {"verdict": verdict, "comment": " ".join(lines[1:]) or "", "ai_used": True}


    # ---- 作业（F24） ----
    @staticmethod
    def _days_left(due):
        try:
            return (_date.fromisoformat(due) - _date.today()).days
        except ValueError:
            return None

    def add_assignment(self, cid, title, due_date="", note="", file_ref=""):
        if not (title or "").strip():
            raise ValueError("作业标题必填")
        if due_date and self._days_left(due_date) is None:
            raise ValueError("截止日期格式应为 YYYY-MM-DD")
        return self._ctx.db.execute(
            "INSERT INTO grad_assignments (course_id, title, due_date, status, note,"
            " file_ref, created_date) VALUES (?,?,?,'todo',?,?,?)",
            (cid, title.strip(), due_date or "", note or "", file_ref or "", today()))

    def update_assignment(self, aid, **fields):
        row = self._ctx.db.query_one("SELECT * FROM grad_assignments WHERE id=?", (aid,))
        if not row:
            return None
        if fields.get("status") not in (None, "todo", "done"):
            raise ValueError("status 只能是 todo/done")
        if fields.get("due_date") and self._days_left(fields["due_date"]) is None:
            raise ValueError("截止日期格式应为 YYYY-MM-DD")
        sets, args = [], []
        for k in ("title", "due_date", "status", "note", "file_ref"):
            if fields.get(k) is not None:
                sets.append(f"{k}=?"); args.append(fields[k])
        if sets:
            args.append(aid)
            self._ctx.db.execute(f"UPDATE grad_assignments SET {', '.join(sets)} WHERE id=?", args)
        return self._ctx.db.query_one("SELECT * FROM grad_assignments WHERE id=?", (aid,))

    def delete_assignment(self, aid):
        self._ctx.db.execute("DELETE FROM grad_assignments WHERE id=?", (aid,))

    def convert_assignment(self, aid):
        """作业 → 今日待办（经注册表调任务域；回填任务 id 防重复转）。"""
        row = self._ctx.db.query_one("SELECT * FROM grad_assignments WHERE id=?", (aid,))
        if not row:
            return None
        if row["converted_task_id"]:
            raise ValueError("该作业已转过今日待办")
        course = self.get_course(row["course_id"])
        dl = self._days_left(row["due_date"]) if row["due_date"] else None
        title = f"课程作业：{row['title']}（{course['name'] if course else '课程'}）"
        if dl is not None:
            title += f" 截止 {row['due_date']}"
        task = self._ctx.services.get("task_service").create(
            title=title, plan_date=today(),
            priority="high" if dl is not None and dl <= 2 else "mid",
            est_minutes=60, source="course")
        self._ctx.db.execute(
            "UPDATE grad_assignments SET converted_task_id=? WHERE id=?", (task["id"], aid))
        return task

    # ---- 组会 ----
    def add_meeting(self, meet_date, title="组会", notes="", my_todos=""):
        mid = self._ctx.db.execute(
            "INSERT INTO grad_meetings (meet_date, title, notes, my_todos) VALUES (?,?,?,?)",
            (meet_date, title, notes, my_todos))
        return mid

    def meetings(self, limit=20):
        return self._ctx.db.query(
            "SELECT * FROM grad_meetings ORDER BY meet_date DESC LIMIT ?", (limit,))

    def update_meeting(self, mid, notes=None, my_todos=None):
        if notes is not None:
            self._ctx.db.execute("UPDATE grad_meetings SET notes=? WHERE id=?", (notes, mid))
        if my_todos is not None:
            self._ctx.db.execute("UPDATE grad_meetings SET my_todos=? WHERE id=?", (my_todos, mid))

    def delete_meeting(self, mid):
        """v1.8：组会记录删除（确认由前端负责）。"""
        self._ctx.db.execute("DELETE FROM grad_meetings WHERE id=?", (mid,))

    # ---- 导师任务 ----
    def add_advisor_task(self, content):
        aid = self._ctx.db.execute(
            "INSERT INTO grad_advisor_tasks (content, created_date) VALUES (?,?)",
            (content, today()))
        return aid

    def advisor_tasks(self, status=None):
        if status:
            return self._ctx.db.query(
                "SELECT * FROM grad_advisor_tasks WHERE status=? ORDER BY id DESC", (status,))
        return self._ctx.db.query(
            "SELECT * FROM grad_advisor_tasks ORDER BY status='pending' DESC, id DESC")

    def delete_advisor_task(self, aid):
        """v1.8：导师任务登记删除（待处理/已转化均可，确认由前端负责）。"""
        self._ctx.db.execute("DELETE FROM grad_advisor_tasks WHERE id=?", (aid,))

    def convert_advisor_task(self, aid):
        """转为今日待办（F8：经注册表调任务域，并回填来源）。"""
        row = self._ctx.db.query_one("SELECT * FROM grad_advisor_tasks WHERE id=?", (aid,))
        if not row or row["status"] != "pending":
            return None
        task = self._ctx.services.get("task_service").create(
            title=row["content"], plan_date=today(), priority="high", source="advisor")
        self._ctx.db.execute(
            "UPDATE grad_advisor_tasks SET status='converted', task_id=? WHERE id=?",
            (task["id"], aid))
        return task


def register(ctx: AppContext):
    ctx.services.register(GradService.name, GradService(ctx))
