# -*- coding: utf-8 -*-
"""本地文件夹浏览路由（fs 设施域，F25 浏览导航用）。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    fs = lambda: ctx.services.get("fs_service")

    def folders(ctx: AppContext, params, body, query):
        return fs().folders(query.get("path", ""))

    router.get("/api/fs/folders", folders)
