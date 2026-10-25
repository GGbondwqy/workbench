# -*- coding: utf-8 -*-
"""英语（雅思）路由：复习队列 / 评分 / 导入 / 训练打卡。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    svc = lambda: ctx.services.get("vocab_service")

    def queue(ctx: AppContext, params, body, query):
        return {"queue": svc().due_queue(), "total_words": svc().counts()}

    def review(ctx: AppContext, params, body, query):
        return svc().review(int(params["id"]), int(body["grade"]))

    def finish(ctx: AppContext, params, body, query):
        return svc().finish_session(int(body.get("count", 0)))

    def import_words(ctx: AppContext, params, body, query):
        text = body.get("text", "")
        if not text.strip():
            return 400, {"error": "text 必填（每行：word 释义）"}
        return svc().import_words(text.splitlines())

    def practice(ctx: AppContext, params, body, query):
        from app.core.timeutil import today
        pid = svc().add_practice(
            body.get("date") or today(), body["kind"],
            int(body.get("minutes", 0)), body.get("note", ""))
        return 201, {"id": pid}

    def practices(ctx: AppContext, params, body, query):
        return {"items": svc().practices()}

    router.get("/api/vocab/queue", queue)
    router.post("/api/vocab/words/import", import_words)
    router.post("/api/vocab/review/{id}", review)
    router.post("/api/vocab/finish", finish)
    router.get("/api/vocab/practices", practices)
    router.post("/api/vocab/practices", practice)
