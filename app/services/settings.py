# -*- coding: utf-8 -*-
"""设置服务：服务端键值存储（示例：带数据表的模块，示范 MIGRATIONS 约定）。"""
import json

from app.core.registry import AppContext
from app.core.timeutil import now

MIGRATIONS = [
    ("0001_settings", """
        CREATE TABLE IF NOT EXISTS settings_app (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """),
]


class SettingsService:
    name = "settings_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def all(self) -> dict:
        rows = self._ctx.db.query("SELECT key, value FROM settings_app")
        return {r["key"]: json.loads(r["value"]) for r in rows}

    def get(self, key: str, default=None):
        row = self._ctx.db.query_one("SELECT value FROM settings_app WHERE key = ?", (key,))
        return json.loads(row["value"]) if row else default

    def set(self, key: str, value):
        self._ctx.db.execute(
            "INSERT INTO settings_app (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, json.dumps(value, ensure_ascii=False), now()))
        self._ctx.events.publish("settings.changed", {"key": key, "value": value})
        return {"key": key, "value": value}


def register(ctx: AppContext):
    ctx.services.register(SettingsService.name, SettingsService(ctx))
