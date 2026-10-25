# -*- coding: utf-8 -*-
"""目标 / 日志 / 习惯路由。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    # ---- 目标 ----
    def goals(ctx: AppContext, params, body, query):
        svc = ctx.services.get("goal_service")
        return {"goals": svc.list(), "archived": svc.list(archived=True)}

    def seed_goals(ctx: AppContext, params, body, query):
        return ctx.services.get("goal_service").seed()

    def set_deadline(ctx: AppContext, params, body, query):
        ctx.services.get("goal_service").set_deadline(
            int(params["id"]), body.get("deadline"))
        return {"ok": True}

    def set_archived(ctx: AppContext, params, body, query):
        ctx.services.get("goal_service").set_archived(
            int(params["id"]), bool(body.get("archived", True)))
        return {"ok": True}

    def delete_goal(ctx: AppContext, params, body, query):
        ctx.services.get("goal_service").delete(int(params["id"]))
        return {"ok": True}

    def bump_ms(ctx: AppContext, params, body, query):
        ctx.services.get("goal_service").bump_milestone(
            int(params["id"]), int(body.get("delta", 1)))
        return {"ok": True}

    def create_goal(ctx: AppContext, params, body, query):
        gid = ctx.services.get("goal_service").create(
            title=body["title"], description=body.get("description", ""),
            deadline=body.get("deadline"),
            milestones=body.get("milestones", []))
        return 201, {"id": gid}

    router.get("/api/goals", goals)
    router.post("/api/goals", create_goal)
    router.post("/api/goals/seed", seed_goals)
    router.put("/api/goals/{id}/deadline", set_deadline)
    router.put("/api/goals/{id}/archive", set_archived)
    router.delete("/api/goals/{id}", delete_goal)
    router.post("/api/goals/milestones/{id}/bump", bump_ms)

    # ---- 日志 ----
    def journal_list(ctx: AppContext, params, body, query):
        return {"entries": ctx.services.get("journal_service").list()}

    def journal_upsert(ctx: AppContext, params, body, query):
        if not body.get("content"):
            return 400, {"error": "content 必填"}
        e = ctx.services.get("journal_service").upsert(
            params["date"], body["content"])
        return e

    router.get("/api/journal", journal_list)
    router.put("/api/journal/{date}", journal_upsert)

    # ---- 习惯 ----
    def habits(ctx: AppContext, params, body, query):
        from app.core.timeutil import today
        return {"habits": ctx.services.get("habit_service").list(query.get("date") or today())}

    def habit_create(ctx: AppContext, params, body, query):
        hid = ctx.services.get("habit_service").create(
            body["name"], body.get("icon", "🔥"))
        return 201, {"id": hid}

    def habit_checkin(ctx: AppContext, params, body, query):
        hs = ctx.services.get("habit_service")
        hid = int(params["id"])
        if body.get("undo"):
            hs.uncheck(hid)
        else:
            hs.checkin(hid)
        return {"ok": True}

    def habit_delete(ctx: AppContext, params, body, query):
        ctx.services.get("habit_service").delete(int(params["id"]))
        return {"ok": True}

    router.get("/api/habits", habits)
    router.post("/api/habits", habit_create)
    router.post("/api/habits/{id}/checkin", habit_checkin)
    router.delete("/api/habits/{id}", habit_delete)
