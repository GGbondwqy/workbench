# -*- coding: utf-8 -*-
"""日程域：固定块（课程/组会）+ 学习块，时间轴与空闲时段计算（DESIGN 对象2）。"""
from datetime import datetime
from app.core.registry import AppContext

MIGRATIONS = [
    ("0003_schedule", """
        CREATE TABLE IF NOT EXISTS schedule_blocks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kind        TEXT NOT NULL,             -- fixed(按周)/study(绑定日期)
            title       TEXT NOT NULL,
            day_of_week INTEGER,                   -- fixed: 0=周一..6=周日
            date        TEXT,                      -- study: YYYY-MM-DD
            start_time  TEXT NOT NULL,             -- HH:MM
            end_time    TEXT NOT NULL,
            task_id     INTEGER,
            place       TEXT DEFAULT ''
        );
    """),
]

DAY_START, DAY_END = "07:00", "23:00"


def _mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


class ScheduleService:
    name = "schedule_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 固定块管理 ----
    def add_fixed(self, title, day_of_week, start_time, end_time, place=""):
        bid = self._ctx.db.execute(
            "INSERT INTO schedule_blocks (kind,title,day_of_week,start_time,end_time,place)"
            " VALUES ('fixed',?,?,?,?,?)",
            (title, day_of_week, start_time, end_time, place))
        return self.get_block(bid)

    def delete_block(self, bid):
        self._ctx.db.execute("DELETE FROM schedule_blocks WHERE id=?", (bid,))

    def fixed_blocks(self):
        return self._ctx.db.query(
            "SELECT * FROM schedule_blocks WHERE kind='fixed'"
            " ORDER BY day_of_week, start_time")

    def add_study(self, date, title, start_time, end_time, task_id=None):
        bid = self._ctx.db.execute(
            "INSERT INTO schedule_blocks (kind,title,date,start_time,end_time,task_id)"
            " VALUES ('study',?,?,?,?,?)",
            (title, date, start_time, end_time, task_id))
        return self.get_block(bid)

    def get_block(self, bid):
        return self._ctx.db.query_one("SELECT * FROM schedule_blocks WHERE id=?", (bid,))

    # ---- 时间轴与空闲 ----
    def day_timeline(self, date: str):
        """某日时间轴：固定块(按星期) + 学习块(按日期)，按开始时间排序。"""
        dow = (datetime.strptime(date, "%Y-%m-%d").weekday())
        blocks = self._ctx.db.query(
            "SELECT * FROM schedule_blocks WHERE (kind='fixed' AND day_of_week=?)"
            " OR (kind='study' AND date=?) ORDER BY start_time", (dow, date))
        return blocks

    def free_slots(self, date: str):
        """当日空闲时段：[DAY_START, DAY_END] 减去已占用块。"""
        busy = [(_mins(b["start_time"]), _mins(b["end_time"])) for b in self.day_timeline(date)]
        busy.sort()
        slots, cur = [], _mins(DAY_START)
        for s, e in busy:
            if s > cur:
                slots.append((cur, s))
            cur = max(cur, e)
        if cur < _mins(DAY_END):
            slots.append((cur, _mins(DAY_END)))
        fmt = lambda m: f"{m // 60:02d}:{m % 60:02d}"
        return [{"start": fmt(s), "end": fmt(e), "minutes": e - s} for s, e in slots]


def register(ctx: AppContext):
    ctx.services.register(ScheduleService.name, ScheduleService(ctx))
