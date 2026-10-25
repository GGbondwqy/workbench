# -*- coding: utf-8 -*-
"""规划与首页聚合路由（调度入口：UI 只发请求，逻辑全在 plan_service）。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    svc = lambda: ctx.services.get("plan_service")

    def dashboard(ctx: AppContext, params, body, query):
        from app.core.timeutil import today
        return svc().dashboard(query.get("date") or today())

    def suggest(ctx: AppContext, params, body, query):
        from app.core.timeutil import today
        return svc().generate(query.get("date") or today())

    def confirm(ctx: AppContext, params, body, query):
        items = body.get("items", [])
        if not items:
            return 400, {"error": "items 必填"}
        return svc().confirm(body.get("date"), items)

    router.get("/api/dashboard", dashboard)
    router.get("/api/plan/suggest", suggest)
    router.post("/api/plan/confirm", confirm)
