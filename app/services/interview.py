# -*- coding: utf-8 -*-
"""面试域（DESIGN v2.0）：面试日程（临近联动工作台）/ 面试复盘 / Offer 对比。"""
from datetime import datetime, date

from app.core.registry import AppContext
from app.core.timeutil import today, now

MIGRATIONS = [
    ("0016_interview", """
        CREATE TABLE IF NOT EXISTS interview_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meet_at TEXT NOT NULL,           -- YYYY-MM-DD HH:MM
            company TEXT NOT NULL,
            round TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS interview_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            company TEXT NOT NULL,
            round TEXT DEFAULT '',
            questions TEXT DEFAULT '',       -- 问题清单（换行分隔）
            performance TEXT DEFAULT '',
            improve TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS interview_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            salary TEXT DEFAULT '',
            location TEXT DEFAULT '',
            direction TEXT DEFAULT '',
            growth TEXT DEFAULT '',
            score INTEGER DEFAULT 3,
            note TEXT DEFAULT ''
        );
    """),
]


class InterviewService:
    name = "interview_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 面试日程 ----
    def add_schedule(self, meet_at, company, round_="", note=""):
        sid = self._ctx.db.execute(
            "INSERT INTO interview_schedules (meet_at, company, round, note, created_at)"
            " VALUES (?,?,?,?,?)", (meet_at, company, round_, note, now()))
        return sid

    def schedules(self, upcoming=True):
        if upcoming:
            return self._ctx.db.query(
                "SELECT * FROM interview_schedules WHERE meet_at >= ?"
                " ORDER BY meet_at", (today(),))
        return self._ctx.db.query("SELECT * FROM interview_schedules ORDER BY meet_at DESC")

    def delete_schedule(self, sid):
        self._ctx.db.execute("DELETE FROM interview_schedules WHERE id=?", (sid,))

    def urgent(self, days=3):
        """N 天内的面试（供规划引擎置顶）。"""
        rows = self.schedules()
        out = []
        for r in rows:
            try:
                dt = datetime.strptime(r["meet_at"], "%Y-%m-%d %H:%M")
                left = (dt.date() - date.today()).days
                if 0 <= left <= days:
                    out.append({"company": r["company"], "round": r["round"],
                                "when": r["meet_at"], "days_left": left})
            except ValueError:
                continue
        return out

    # ---- 复盘 ----
    def add_review(self, day, company, round_="", questions="", performance="", improve=""):
        rid = self._ctx.db.execute(
            "INSERT INTO interview_reviews (date, company, round, questions, performance,"
            " improve, created_at) VALUES (?,?,?,?,?,?,?)",
            (day, company, round_, questions, performance, improve, now()))
        return rid

    def reviews(self, limit=50):
        return self._ctx.db.query(
            "SELECT * FROM interview_reviews ORDER BY date DESC LIMIT ?", (limit,))

    def delete_review(self, rid):
        self._ctx.db.execute("DELETE FROM interview_reviews WHERE id=?", (rid,))

    # ---- Offer 对比 ----
    def add_offer(self, company, salary="", location="", direction="", growth="", score=3, note=""):
        oid = self._ctx.db.execute(
            "INSERT INTO interview_offers (company, salary, location, direction, growth,"
            " score, note) VALUES (?,?,?,?,?,?,?)",
            (company, salary, location, direction, growth, score, note))
        return oid

    def offers(self):
        return self._ctx.db.query("SELECT * FROM interview_offers ORDER BY score DESC")

    def delete_offer(self, oid):
        self._ctx.db.execute("DELETE FROM interview_offers WHERE id=?", (oid,))


def register(ctx: AppContext):
    ctx.services.register(InterviewService.name, InterviewService(ctx))
