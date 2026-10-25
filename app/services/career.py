# -*- coding: utf-8 -*-
"""就业域：刷题记录、实习投递看板、八股复习计划（DESIGN 对象12/13，流程 F9/F10）。"""
from app.core.registry import AppContext
from app.core.timeutil import today, now

MIGRATIONS = [
    ("0010_career", """
        CREATE TABLE IF NOT EXISTS career_problems (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT NOT NULL,
            title    TEXT NOT NULL,
            difficulty TEXT DEFAULT '',
            topic    TEXT DEFAULT '',
            minutes  INTEGER DEFAULT 0,
            mastery  INTEGER DEFAULT 3,     -- 1-5
            note     TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS career_applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company     TEXT NOT NULL,
            position    TEXT NOT NULL,
            channel     TEXT DEFAULT '',
            apply_date  TEXT NOT NULL,
            status      TEXT DEFAULT 'applied',
            timeline    TEXT NOT NULL DEFAULT '[]'   -- JSON: [{status,time,note}]
        );
        CREATE TABLE IF NOT EXISTS career_kb_reads (
            date    TEXT NOT NULL,
            relpath TEXT NOT NULL,
            UNIQUE (date, relpath)
        );
    """),
]

PIPELINE = ["applied", "written", "interview1", "interview2", "hr", "offer", "closed"]
PIPELINE_LABEL = {"applied": "已投递", "written": "笔试", "interview1": "一面",
                  "interview2": "二面", "hr": "HR面", "offer": "Offer", "closed": "已结束"}


class CareerService:
    name = "career_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 刷题 ----
    def add_problem(self, day, title, difficulty="", topic="", minutes=0, mastery=3, note=""):
        pid = self._ctx.db.execute(
            "INSERT INTO career_problems (date,title,difficulty,topic,minutes,mastery,note)"
            " VALUES (?,?,?,?,?,?,?)", (day, title, difficulty, topic, minutes, mastery, note))
        # 刷题可推动"算法刷题"里程碑（若存在同名里程碑，经注册表查询）
        self._bump_milestone("算法刷题")
        return pid

    def _bump_milestone(self, keyword):
        try:
            row = self._ctx.db.query_one(
                "SELECT m.id FROM goal_milestones m WHERE m.title LIKE ?", (f"%{keyword}%",))
            if row:
                self._ctx.services.get("goal_service").record_progress(row["id"])
        except Exception:
            pass  # goal 域未就绪时不阻塞

    def problems(self, limit=100):
        return self._ctx.db.query(
            "SELECT * FROM career_problems ORDER BY date DESC, id DESC LIMIT ?", (limit,))

    def problem_stats(self):
        total = self._ctx.db.query_one("SELECT COUNT(*) n FROM career_problems")["n"]
        topics = self._ctx.db.query(
            "SELECT topic, COUNT(*) n FROM career_problems WHERE topic!=''"
            " GROUP BY topic ORDER BY n DESC LIMIT 8")
        return {"total": total, "topics": topics}

    # ---- 投递 ----
    def add_application(self, company, position, channel="", apply_date=None):
        aid = self._ctx.db.execute(
            "INSERT INTO career_applications (company,position,channel,apply_date,status,timeline)"
            " VALUES (?,?,?,?, 'applied', ?)",
            (company, position, channel, apply_date or today(),
             self._timeline_json("applied", apply_date or today())))
        return self.get_application(aid)

    @staticmethod
    def _timeline_json(status, time, note=""):
        return json_dumps([{"status": status, "time": time, "note": note}])

    def get_application(self, aid):
        row = self._ctx.db.query_one("SELECT * FROM career_applications WHERE id=?", (aid,))
        if row:
            row["timeline"] = safe_loads(row["timeline"], [])
        return row

    def applications(self):
        rows = self._ctx.db.query("SELECT * FROM career_applications ORDER BY apply_date DESC")
        for r in rows:
            r["timeline"] = safe_loads(r["timeline"], [])
        return rows

    def advance(self, aid, status, note=""):
        row = self._ctx.db.query_one("SELECT timeline FROM career_applications WHERE id=?", (aid,))
        if not row:
            return None
        tl = safe_loads(row["timeline"], [])
        tl.append({"status": status, "time": now(), "note": note})
        self._ctx.db.execute(
            "UPDATE career_applications SET status=?, timeline=? WHERE id=?",
            (status, json_dumps(tl), aid))
        return self.get_application(aid)

    def delete_application(self, aid):
        """v1.19：投递看板删除（timeline 为行内 JSON，随行删）。"""
        self._ctx.db.execute("DELETE FROM career_applications WHERE id=?", (aid,))

    def nav(self):
        """v1.19 F30：投递导航清单（静态 seed，无库表）。"""
        from app.services import career_nav_seed
        return {"platforms": career_nav_seed.PLATFORMS,
                "companies": career_nav_seed.COMPANIES}

    # ---- 八股复习计划（F10 简化实现：每日推荐未读篇目，读完打勾）----
    def kb_plan(self, daily=2):
        kb = self._ctx.services.try_get("kb_service")
        if not kb:
            return {"available": False}
        all_paths = kb.list_paths()
        done_paths = {r["relpath"] for r in self._ctx.db.query("SELECT relpath FROM career_kb_reads")}
        todo = [p for p in all_paths if p["relpath"] not in done_paths]
        done_today = self._ctx.db.query(
            "SELECT relpath FROM career_kb_reads WHERE date=?", (today(),))
        items = todo[:daily]
        for it in items:
            meta = kb.meta(it["relpath"]) or {}
            it["title"] = meta.get("title", it["relpath"])
            it["category"] = meta.get("category", "")
        return {
            "available": True,
            "remaining": len(todo),
            "total": len(all_paths),
            "today_done": len(done_today),
            "items": items,
        }

    def kb_mark_read(self, relpath):
        self._ctx.db.execute(
            "INSERT OR IGNORE INTO career_kb_reads (date, relpath) VALUES (?,?)",
            (today(), relpath))
        self._bump_milestone("八股")

    def kb_browse(self, category="", status="", q="", limit=100):
        """八股"找文章"（v1.3）：关键词 + 栏目 + 已读未读筛选。跨域数据经注册表查询。"""
        kb = self._ctx.services.try_get("kb_service")
        if not kb:
            return {"available": False, "items": [], "categories": []}
        metas = kb.tree("bagu")
        categories = sorted({m["category"] for m in metas if m["category"]})
        if category:
            metas = [m for m in metas if m["category"] == category]
        if q:
            hits = {h["relpath"] for h in kb.search(q, limit=200, library="bagu")}
            metas = [m for m in metas if m["relpath"] in hits]
        read = {r["relpath"] for r in self._ctx.db.query("SELECT relpath FROM career_kb_reads")}
        items = [{"relpath": m["relpath"], "title": m["title"], "category": m["category"],
                  "read": m["relpath"] in read} for m in metas]
        if status == "read":
            items = [i for i in items if i["read"]]
        elif status == "unread":
            items = [i for i in items if not i["read"]]
        return {"available": True, "items": items[:limit], "categories": categories,
                "total": len(metas)}


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


def safe_loads(s, default):
    import json
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return default


def register(ctx: AppContext):
    ctx.services.register(CareerService.name, CareerService(ctx))
