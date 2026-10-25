# -*- coding: utf-8 -*-
"""AI 用量路由（DESIGN v2.8）：汇总查询 + 单价覆盖。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    U = lambda: ctx.services.get("usage_service")

    def usage_summary(ctx: AppContext, params, body, query):
        days = min(max(int(query.get("days") or 30), 7), 90)
        return U().summary(days)

    def usage_prices(ctx: AppContext, params, body, query):
        return {"models": U().used_models()}

    def usage_set_price(ctx: AppContext, params, body, query):
        model = (body.get("model") or "").strip()
        if not model:
            return 400, {"error": "model 必填"}
        try:
            pin = float(body.get("price_in"))
            pout = float(body.get("price_out") or 0)
        except (TypeError, ValueError):
            return 400, {"error": "单价须为数字（元/百万token）"}
        hit = body.get("price_hit")
        try:
            hit = float(hit) if hit not in (None, "") else None
        except (TypeError, ValueError):
            return 400, {"error": "命中单价须为数字"}
        if pin < 0 or pout < 0 or (hit is not None and hit < 0):
            return 400, {"error": "单价不能为负"}
        U().set_price(model, pin, pout, hit)
        return {"ok": True}

    router.get("/api/usage/summary", usage_summary)
    router.get("/api/usage/prices", usage_prices)
    router.put("/api/usage/prices", usage_set_price)
