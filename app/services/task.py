# -*- coding: utf-8 -*-
"""任务域：CRUD、状态流转、完成时推进里程碑并广播事件（DESIGN F2）。"""
from app.core.registry import AppContext
from app.core.timeutil import today, now

MIGRATIONS = [
    ("0002_task", """
        CREATE TABLE IF NOT EXISTS task_tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            note         TEXT DEFAULT '',
            status       TEXT NOT NULL DEFAULT 'todo',   -- todo/doing/done/cancel
            priority     TEXT NOT NULL DEFAULT 'mid',    -- high/mid/low
            plan_date    TEXT,                           -- 计划日期 YYYY-MM-DD
            est_minutes  INTEGER,
            source       TEXT NOT NULL DEFAULT 'manual', -- manual/plan/advisor/kb
            milestone_id INTEGER,
            created_at   TEXT NOT NULL,
            completed_at TEXT
        );
    """),
]


class TaskService:
    name = "task_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def create(self, title, plan_date=None, priority="mid", est_minutes=None,
               source="manual", milestone_id=None, note=""):
        tid = self._ctx.db.execute(
            "INSERT INTO task_tasks (title, note, priority, plan_date, est_minutes,"
            " source, milestone_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (title, note, priority, plan_date, est_minutes, source, milestone_id, now()))
        return self.get(tid)

    def get(self, tid):
        return self._ctx.db.query_one("SELECT * FROM task_tasks WHERE id = ?", (tid,))

    def list(self, date=None, status=None, limit=200):
        sql, params = "SELECT * FROM task_tasks", []
        conds = []
        if date:
            conds.append("plan_date = ?")
            params.append(date)
        if status:
            conds.append("status = ?")
            params.append(status)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END," \
               " created_at DESC LIMIT ?"
        params.append(limit)
        return self._ctx.db.query(sql, params)

    def update(self, tid, **fields):
        allowed = {"title", "note", "status", "priority", "plan_date", "est_minutes"}
        sets, params = [], []
        for k, v in fields.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return self.get(tid)
        params.append(tid)
        self._ctx.db.execute(f"UPDATE task_tasks SET {', '.join(sets)} WHERE id = ?", params)
        return self.get(tid)

    def delete(self, tid):
        self._ctx.db.execute("DELETE FROM task_tasks WHERE id = ?", (tid,))

    def complete(self, tid):
        task = self.get(tid)
        if not task or task["status"] == "done":
            return task
        self._ctx.db.execute(
            "UPDATE task_tasks SET status='done', completed_at=? WHERE id=?", (now(), tid))
        # 推进关联里程碑（跨域只经注册表查询，符合隔离规则）
        if task["milestone_id"]:
            goal_svc = self._ctx.services.try_get("goal_service")
            if goal_svc:
                goal_svc.record_progress(task["milestone_id"])
        self._ctx.events.publish("task.completed", {"task_id": tid, "milestone_id": task["milestone_id"]})
        return self.get(tid)

    def stats(self, date):
        """某日完成/总数；供 dashboard 聚合。"""
        rows = self._ctx.db.query(
            "SELECT status, COUNT(*) n FROM task_tasks WHERE plan_date=? GROUP BY status", (date,))
        m = {r["status"]: r["n"] for r in rows}
        return {"total": sum(m.values()), "done": m.get("done", 0)}


def register(ctx: AppContext):
    ctx.services.register(TaskService.name, TaskService(ctx))
