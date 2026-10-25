# -*- coding: utf-8 -*-
"""学习闭环路由：提问 / 卡片管理 / 复习。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    svc = lambda: ctx.services.get("learn_service")

    def ask(ctx: AppContext, params, body, query):
        q = (body.get("q") or "").strip()
        if not q:
            return 400, {"error": "q 必填"}
        return svc().ask(q, ref_path=body.get("ref_path"), library=body.get("library", "bagu"))

    def cards(ctx: AppContext, params, body, query):
        return {"cards": svc().cards(), "stats": svc().stats()}

    def add_card(ctx: AppContext, params, body, query):
        q = (body.get("q") or "").strip()
        if not q:
            return 400, {"error": "q 必填"}
        c = svc().add_card(
            title=body.get("title") or q[:40], q=q,
            a=body.get("a", ""), point=body.get("point", ""),
            summary=body.get("summary", ""), ref_path=body.get("ref_path", ""),
            library=body.get("library", "bagu"), chapter=body.get("chapter", "待归档"))
        return 201, c

    def update_card(ctx: AppContext, params, body, query):
        return svc().update(int(params["id"]), **body) or (404, {"error": "not found"})

    def delete_card(ctx: AppContext, params, body, query):
        svc().delete(int(params["id"]))
        return {"ok": True}

    def due(ctx: AppContext, params, body, query):
        n = int(query.get("n", 10))
        cards = svc().due_cards(n)
        quizzes = [svc().quiz(c) for c in cards]
        return {"quizzes": quizzes, "stats": svc().stats()}

    def review(ctx: AppContext, params, body, query):
        r = body.get("result")
        if r not in ("pass", "fuzzy", "fail"):
            return 400, {"error": "result 必须是 pass/fuzzy/fail"}
        c = svc().review(int(params["id"]), r)
        return c or (404, {"error": "not found"})

    router.post("/api/learn/ask", ask)
    router.get("/api/learn/cards", cards)
    router.post("/api/learn/cards", add_card)
    router.put("/api/learn/cards/{id}", update_card)
    router.delete("/api/learn/cards/{id}", delete_card)
    router.get("/api/learn/due", due)
    router.post("/api/learn/review/{id}", review)
