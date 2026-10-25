# -*- coding: utf-8 -*-
"""设置路由。"""
from app.core.registry import AppContext  # noqa: F401  (类型标注用)


def register_routes(router, ctx):
    def get_all(ctx: AppContext, params, body, query):
        return ctx.services.get("settings_service").all()

    def put_key(ctx: AppContext, params, body, query):
        if "value" not in body:
            return 400, {"error": "body 需要 {value: ...}"}
        svc = ctx.services.get("settings_service")
        return svc.set(params["key"], body["value"])

    router.get("/api/settings", get_all)
    router.put("/api/settings/{key}", put_key)
