# -*- coding: utf-8 -*-
"""SQLite 数据层：连接管理 + 版本化迁移。业务表由各 service 通过 MIGRATIONS 登记。"""
import sqlite3
import threading
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")

    # ---- 迁移 ----
    def migrate(self, migrations):
        """migrations: [(id, sql), ...] 幂等执行，按 id 排序。"""
        self.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        applied = {r["id"] for r in self.query("SELECT id FROM schema_migrations")}
        with self._lock:
            for mid, sql in sorted(migrations, key=lambda m: m[0]):
                if mid in applied:
                    continue
                self._conn.executescript(sql)
                self._conn.execute(
                    "INSERT INTO schema_migrations (id, applied_at) VALUES (?, ?)",
                    (mid, datetime.now().isoformat(timespec="seconds")))
                self._conn.commit()

    # ---- 通用操作 ----
    def execute(self, sql, params=()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.lastrowid

    def query(self, sql, params=()) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def close(self):
        with self._lock:
            self._conn.close()
