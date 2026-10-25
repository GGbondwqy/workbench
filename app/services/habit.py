# -*- coding: utf-8 -*-
"""习惯域：打卡 + 连续天数（DESIGN 对象5）；订阅复习完成事件自动点亮"背单词"（F3/F4 联动）。"""
from datetime import date, timedelta
from app.core.registry import AppContext

MIGRATIONS = [
    ("0006_habit", """
        CREATE TABLE IF NOT EXISTS habit_habits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            icon       TEXT DEFAULT '🔥',
            enabled    INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS habit_checkins (
            habit_id INTEGER NOT NULL,
            date     TEXT NOT NULL,
            UNIQUE (habit_id, date)
        );
    """),
]

DEFAULT_HABITS = [("背单词", "📖"), ("锻炼", "🏃"), ("早睡", "😴")]


class HabitService:
    name = "habit_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx
        ctx.events.subscribe("vocab.review_done", self._on_vocab_done)

    def _on_vocab_done(self, payload):
        """单词复习完成 → 自动点亮"背单词"习惯（跨域联动走事件）。"""
        h = self._ctx.db.query_one(
            "SELECT id FROM habit_habits WHERE name='背单词' AND enabled=1")
        if h:
            self.checkin(h["id"])

    def ensure_defaults(self):
        if not self._ctx.db.query_one("SELECT 1 FROM habit_habits LIMIT 1"):
            for name, icon in DEFAULT_HABITS:
                self.create(name, icon)

    def create(self, name, icon="🔥"):
        hid = self._ctx.db.execute(
            "INSERT INTO habit_habits (name, icon, created_at) VALUES (?,?,date('now'))",
            (name, icon))
        return hid

    def delete(self, hid):
        self._ctx.db.execute("DELETE FROM habit_habits WHERE id=?", (hid,))
        self._ctx.db.execute("DELETE FROM habit_checkins WHERE habit_id=?", (hid,))

    def list(self, today_str=None):
        today_str = today_str or date.today().isoformat()
        habits = self._ctx.db.query("SELECT * FROM habit_habits WHERE enabled=1 ORDER BY id")
        for h in habits:
            h["checked_today"] = bool(self._ctx.db.query_one(
                "SELECT 1 FROM habit_checkins WHERE habit_id=? AND date=?", (h["id"], today_str)))
            h["streak"] = self._streak(h["id"], today_str)
        return habits

    def _streak(self, hid, today_str):
        """连续天数：今天打了从今天起算，否则从昨天起算。"""
        days = {r["date"] for r in self._ctx.db.query(
            "SELECT date FROM habit_checkins WHERE habit_id=?", (hid,))}
        cur = date.fromisoformat(today_str)
        if cur.isoformat() not in days:
            cur -= timedelta(days=1)
        n = 0
        while cur.isoformat() in days:
            n += 1
            cur -= timedelta(days=1)
        return n

    def checkin(self, hid, day=None):
        """打卡（幂等，重复点击不叠加）。"""
        day = day or date.today().isoformat()
        self._ctx.db.execute(
            "INSERT OR IGNORE INTO habit_checkins (habit_id, date) VALUES (?,?)", (hid, day))

    def uncheck(self, hid, day=None):
        day = day or date.today().isoformat()
        self._ctx.db.execute(
            "DELETE FROM habit_checkins WHERE habit_id=? AND date=?", (hid, day))

    def checkin_days_between(self, start, end):
        """[start, end] 内有打卡的天数（周报统计用）。"""
        row = self._ctx.db.query_one(
            "SELECT COUNT(DISTINCT date) n FROM habit_checkins WHERE date BETWEEN ? AND ?",
            (start, end))
        return row["n"]


def register(ctx: AppContext):
    ctx.services.register(HabitService.name, HabitService(ctx))


def post_migrate(ctx: AppContext):
    """迁移完成后再初始化默认习惯（register 阶段表还不存在）。"""
    ctx.services.get(HabitService.name).ensure_defaults()
