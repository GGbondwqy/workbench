# -*- coding: utf-8 -*-
"""元信息路由：健康检查 + 启动引导信息（首页状态面板用）。"""
from pathlib import Path


def kb_status(ctx) -> dict:
    raw = ctx.config.get("kb", {}).get("path")
    if not raw:
        return {"configured": False, "path": None, "exists": False, "articles": 0}
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (ctx.root / p).resolve()
    if not p.is_dir():
        return {"configured": True, "path": str(p), "exists": False, "articles": 0}
    count = sum(1 for _ in p.rglob("*.md"))
    return {"configured": True, "path": str(p), "exists": True, "articles": count}


def register_routes(router, ctx):
    router.get("/api/health", lambda ctx, params, body, query:
               ctx.services.get("health_service").snapshot())

    def bootstrap(ctx, params, body, query):
        return {
            "app": ctx.config["app"],
            "services": ctx.services.names(),
            "ai": ctx.ai.status(),
            "kb": kb_status(ctx),
        }
    router.get("/api/bootstrap", bootstrap)
