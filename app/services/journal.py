# -*- coding: utf-8 -*-
"""日志域：每日一句话（DESIGN 对象4，一天一条可改）。"""
from app.core.registry import AppContext
from app.core.timeutil import now

MIGRATIONS = [
    ("0005_journal", """
        CREATE TABLE IF NOT EXISTS journal_entries (
            date        TEXT PRIMARY KEY,
            content     TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );
    """),
]


class JournalService:
    name = "journal_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def upsert(self, date, content):
        self._ctx.db.execute(
            "INSERT INTO journal_entries (date, content, updated_at) VALUES (?,?,?)"
            " ON CONFLICT(date) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at",
            (date, content, now()))
        return self.get(date)

    def get(self, date):
        return self._ctx.db.query_one("SELECT * FROM journal_entries WHERE date=?", (date,))

    def list(self, limit=60):
        return self._ctx.db.query(
            "SELECT * FROM journal_entries ORDER BY date DESC LIMIT ?", (limit,))


def register(ctx: AppContext):
    ctx.services.register(JournalService.name, JournalService(ctx))
