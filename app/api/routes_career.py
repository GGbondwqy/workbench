# -*- coding: utf-8 -*-
"""就业路由：刷题 / 投递看板 / 八股复习计划。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    svc = lambda: ctx.services.get("career_service")

    def problems(ctx: AppContext, params, body, query):
        return {"items": svc().problems(), "stats": svc().problem_stats()}

    def add_problem(ctx: AppContext, params, body, query):
        from app.core.timeutil import today
        pid = svc().add_problem(
            body.get("date") or today(), body["title"],
            body.get("difficulty", ""), body.get("topic", ""),
            int(body.get("minutes", 0)), int(body.get("mastery", 3)),
            body.get("note", ""))
        return 201, {"id": pid}

    def applications(ctx: AppContext, params, body, query):
        return {"items": svc().applications()}

    def add_application(ctx: AppContext, params, body, query):
        a = svc().add_application(body["company"], body["position"],
                                  body.get("channel", ""), body.get("apply_date"))
        return 201, a

    def advance(ctx: AppContext, params, body, query):
        a = svc().advance(int(params["id"]), body["status"], body.get("note", ""))
        return a or (404, {"error": "not found"})

    def del_application(ctx: AppContext, params, body, query):
        svc().delete_application(int(params["id"]))   # v1.19：timeline 随行删
        return {"ok": True}

    def nav(ctx: AppContext, params, body, query):
        return svc().nav()                             # v1.19 F30 投递导航

    def kb_plan(ctx: AppContext, params, body, query):
        return svc().kb_plan(daily=int(query.get("daily", 2)))

    def kb_read(ctx: AppContext, params, body, query):
        svc().kb_mark_read(body["relpath"])
        return {"ok": True}

    def kb_browse(ctx: AppContext, params, body, query):
        return svc().kb_browse(category=query.get("category", ""),
                               status=query.get("status", ""),
                               q=query.get("q", ""))

    router.get("/api/career/problems", problems)
    router.post("/api/career/problems", add_problem)
    router.get("/api/career/applications", applications)
    router.post("/api/career/applications", add_application)
    router.post("/api/career/applications/{id}/advance", advance)
    router.delete("/api/career/applications/{id}", del_application)   # v1.19
    router.get("/api/career/nav", nav)                                # v1.19 F30
    router.get("/api/career/kb-plan", kb_plan)
    router.post("/api/career/kb-read", kb_read)
    router.get("/api/career/kb-browse", kb_browse)
