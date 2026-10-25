# -*- coding: utf-8 -*-
"""项目域（DESIGN v2.0）：项目卡/里程碑/技术栈/亮点笔记/面试问答/简历版本。"""
from app.core.registry import AppContext
from app.core.timeutil import today

MIGRATIONS = [
    ("0015_project", """
        CREATE TABLE IF NOT EXISTS project_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'building',   -- choosing/building/online/paused
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS project_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done_count INTEGER DEFAULT 0,
            total INTEGER DEFAULT 1,
            sort INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS project_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            kind TEXT NOT NULL,               -- stack/highlight/qa/resume
            title TEXT DEFAULT '',
            content TEXT DEFAULT '',
            extra TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    """),
    ("0019_project_archive", """
        ALTER TABLE project_projects ADD COLUMN prev_status TEXT;
    """),
]

STATUS_CN = {"choosing": "选题中", "building": "开发中", "online": "已上线",
             "paused": "暂缓", "archived": "已归档"}


class ProjectService:
    name = "project_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def create(self, name, description="", status="building", milestones=None):
        pid = self._ctx.db.execute(
            "INSERT INTO project_projects (name, status, description, created_at)"
            " VALUES (?,?,?,?)", (name, status, description, today()))
        for i, ms in enumerate(milestones or ["需求设计", "开发实现", "部署上线"]):
            self._ctx.db.execute(
                "INSERT INTO project_milestones (project_id, title, total, sort)"
                " VALUES (?,?,1,?)", (pid, ms, i))
        return self.get(pid)

    def get(self, pid):
        p = self._ctx.db.query_one("SELECT * FROM project_projects WHERE id=?", (pid,))
        if p:
            p["status_cn"] = STATUS_CN.get(p["status"], p["status"])
            p["milestones"] = self._ctx.db.query(
                "SELECT * FROM project_milestones WHERE project_id=? ORDER BY sort", (pid,))
            total = sum(m["total"] for m in p["milestones"]) or 1
            done = sum(m["done_count"] for m in p["milestones"])
            p["progress"] = round(done / total * 100)
        return p

    def list(self, archived=False):
        op = "==" if archived else "!="
        ids = [r["id"] for r in self._ctx.db.query(
            f"SELECT id FROM project_projects WHERE status {op} 'archived' ORDER BY id DESC")]
        return [self.get(i) for i in ids]

    def set_status(self, pid, status):
        self._ctx.db.execute("UPDATE project_projects SET status=? WHERE id=?", (status, pid))

    def archive(self, pid, archived=True):
        """归档/恢复：归档时记住原状态，恢复时回到归档前的状态。"""
        if archived:
            p = self.get(pid)
            if not p or p["status"] == "archived":
                return
            self._ctx.db.execute(
                "UPDATE project_projects SET status='archived', prev_status=? WHERE id=?",
                (p["status"], pid))
        else:
            row = self._ctx.db.query_one(
                "SELECT prev_status FROM project_projects WHERE id=?", (pid,))
            prev = (row and row["prev_status"]) or "building"
            self._ctx.db.execute(
                "UPDATE project_projects SET status=?, prev_status=NULL WHERE id=?",
                (prev, pid))

    def delete(self, pid):
        self._ctx.db.execute("DELETE FROM project_milestones WHERE project_id=?", (pid,))
        self._ctx.db.execute("DELETE FROM project_items WHERE project_id=?", (pid,))
        self._ctx.db.execute("DELETE FROM project_projects WHERE id=?", (pid,))

    def bump_milestone(self, mid):
        self._ctx.db.execute(
            "UPDATE project_milestones SET done_count = MIN(total, done_count+1) WHERE id=?", (mid,))

    # ---- 项目条目：技术栈/亮点/面试问答/简历 ----
    def add_item(self, project_id, kind, title="", content="", extra=""):
        iid = self._ctx.db.execute(
            "INSERT INTO project_items (project_id, kind, title, content, extra, created_at)"
            " VALUES (?,?,?,?,?,?)", (project_id, kind, title, content, extra, today()))
        return iid

    def items(self, project_id, kind):
        return self._ctx.db.query(
            "SELECT * FROM project_items WHERE project_id=? AND kind=? ORDER BY id DESC",
            (project_id, kind))

    def update_item(self, iid, content=None, title=None, extra=None):
        if content is not None:
            self._ctx.db.execute("UPDATE project_items SET content=? WHERE id=?", (content, iid))
        if title is not None:
            self._ctx.db.execute("UPDATE project_items SET title=? WHERE id=?", (title, iid))
        if extra is not None:
            self._ctx.db.execute("UPDATE project_items SET extra=? WHERE id=?", (extra, iid))

    def delete_item(self, iid):
        self._ctx.db.execute("DELETE FROM project_items WHERE id=?", (iid,))

    def resumes(self):
        return self.items(0, "resume")  # 简历不挂项目，project_id=0


def register(ctx: AppContext):
    ctx.services.register(ProjectService.name, ProjectService(ctx))
