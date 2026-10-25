# -*- coding: utf-8 -*-
"""文献域：Zotero BBT JSON 导入、阅读状态、笔记（DESIGN 对象10，流程 F7）。"""
import json
from app.core.registry import AppContext
from app.core.timeutil import now

MIGRATIONS = [
    ("0009_paper", """
        CREATE TABLE IF NOT EXISTS grad_papers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            zotero_key   TEXT UNIQUE,
            title        TEXT NOT NULL,
            authors      TEXT DEFAULT '',
            year         TEXT DEFAULT '',
            venue        TEXT DEFAULT '',
            item_type    TEXT DEFAULT '',
            status       TEXT DEFAULT 'unread',  -- unread/reading/done/dropped
            milestone_id INTEGER,
            imported_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS grad_paper_notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id   INTEGER NOT NULL,
            content    TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """),
]


class PaperService:
    name = "paper_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def import_bbt(self, payload):
        """导入 Zotero Better BibTeX 导出的 JSON 数组；按 zotero key 去重合并，保留状态与笔记。"""
        items = payload if isinstance(payload, list) else payload.get("items", [])
        added, merged = 0, 0
        for it in items:
            key = it.get("id") or it.get("key") or it.get("citationKey") or ""
            title = (it.get("title") or "").strip()
            if not title:
                continue
            authors = "; ".join(
                c.get("name", c.get("literal", "")) if isinstance(c, dict) else str(c)
                for c in (it.get("creators") or it.get("author") or []))[:300]
            year = str(it.get("issued", {}).get("date-parts", [[""]])[0][0]
                       if isinstance(it.get("issued"), dict) else it.get("year") or "")
            venue = it.get("container-title") or it.get("publisher") or ""
            itype = it.get("type") or ""
            exists = self._ctx.db.query_one(
                "SELECT id FROM grad_papers WHERE zotero_key=? AND zotero_key!=''", (key,)) \
                if key else None
            if exists:
                self._ctx.db.execute(
                    "UPDATE grad_papers SET title=?, authors=?, year=?, venue=?, item_type=?"
                    " WHERE id=?", (title, authors, year, venue, itype, exists["id"]))
                merged += 1
            else:
                try:
                    self._ctx.db.execute(
                        "INSERT INTO grad_papers (zotero_key,title,authors,year,venue,item_type,"
                        "imported_at) VALUES (?,?,?,?,?,?,?)",
                        (key, title, authors, year, venue, itype, now()))
                    added += 1
                except Exception:
                    merged += 1
        return {"added": added, "merged": merged, "total_seen": len(items)}

    def import_from_text(self, text):
        try:
            return self.import_bbt(json.loads(text))
        except ValueError:
            return {"error": "不是合法的 JSON（请用 Zotero Better BibTeX 导出 JSON）"}

    def list(self, status=None):
        if status:
            return self._ctx.db.query(
                "SELECT * FROM grad_papers WHERE status=? ORDER BY id DESC", (status,))
        return self._ctx.db.query("SELECT * FROM grad_papers ORDER BY status='unread' DESC, id DESC")

    def set_status(self, pid, status):
        self._ctx.db.execute("UPDATE grad_papers SET status=? WHERE id=?", (status, pid))

    def add_note(self, pid, content):
        nid = self._ctx.db.execute(
            "INSERT INTO grad_paper_notes (paper_id, content, created_at) VALUES (?,?,?)",
            (pid, content, now()))
        return nid

    def notes(self, pid):
        return self._ctx.db.query(
            "SELECT * FROM grad_paper_notes WHERE paper_id=? ORDER BY id DESC", (pid,))

    def delete_note(self, nid):
        """v1.19：文献笔记删除。"""
        self._ctx.db.execute("DELETE FROM grad_paper_notes WHERE id=?", (nid,))

    def delete_paper(self, pid):
        """v1.19：文献删除（级联笔记）。"""
        self._ctx.db.execute("DELETE FROM grad_paper_notes WHERE paper_id=?", (pid,))
        self._ctx.db.execute("DELETE FROM grad_papers WHERE id=?", (pid,))


def register(ctx: AppContext):
    ctx.services.register(PaperService.name, PaperService(ctx))
