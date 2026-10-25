# -*- coding: utf-8 -*-
"""任务与日程路由。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    def svc(name):
        return ctx.services.get(name)

    # ---- 任务 ----
    def list_tasks(ctx: AppContext, params, body, query):
        return {"tasks": svc("task_service").list(date=query.get("date"))}

    def create_task(ctx: AppContext, params, body, query):
        if not body.get("title"):
            return 400, {"error": "title 必填"}
        t = svc("task_service").create(
            title=body["title"], plan_date=body.get("plan_date"),
            priority=body.get("priority", "mid"),
            est_minutes=body.get("est_minutes"), note=body.get("note", ""))
        return 201, t

    def complete_task(ctx: AppContext, params, body, query):
        t = svc("task_service").complete(int(params["id"]))
        return t or (404, {"error": "not found"})

    def update_task(ctx: AppContext, params, body, query):
        t = svc("task_service").update(int(params["id"]), **body)
        return t or (404, {"error": "not found"})

    def delete_task(ctx: AppContext, params, body, query):
        svc("task_service").delete(int(params["id"]))
        return {"ok": True}

    router.get("/api/tasks", list_tasks)
    router.post("/api/tasks", create_task)
    router.put("/api/tasks/{id}", update_task)
    router.delete("/api/tasks/{id}", delete_task)
    router.post("/api/tasks/{id}/complete", complete_task)

    # ---- 日程 ----
    def timeline(ctx: AppContext, params, body, query):
        from app.core.timeutil import today
        date = query.get("date") or today()
        s = svc("schedule_service")
        return {"date": date, "blocks": s.day_timeline(date), "free": s.free_slots(date)}

    def add_fixed(ctx: AppContext, params, body, query):
        b = svc("schedule_service").add_fixed(
            title=body["title"], day_of_week=int(body["day_of_week"]),
            start_time=body["start_time"], end_time=body["end_time"],
            place=body.get("place", ""))
        return 201, b

    def add_study(ctx: AppContext, params, body, query):
        b = svc("schedule_service").add_study(
            date=body["date"], title=body["title"],
            start_time=body["start_time"], end_time=body["end_time"])
        return 201, b

    def del_block(ctx: AppContext, params, body, query):
        svc("schedule_service").delete_block(int(params["id"]))
        return {"ok": True}

    router.get("/api/schedule/today", timeline)
    router.post("/api/schedule/fixed", add_fixed)
    router.post("/api/schedule/study", add_study)
    router.delete("/api/schedule/blocks/{id}", del_block)
