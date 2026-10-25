# -*- coding: utf-8 -*-
"""资料库路由：搜索 / 阅读 / 问答 / 收藏 / 扫描。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    svc = lambda: ctx.services.get("kb_service")

    def search(ctx, params, body, query):
        q = query.get("q", "").strip()
        if not q:
            return 400, {"error": "q 必填"}
        return {"query": q, "hits": svc().search(q, library=query.get("lib"))}

    def article(ctx, params, body, query):
        rel = query.get("path", "")
        a = svc().article(rel)
        return a or (404, {"error": "article not found"})

    def ask(ctx, params, body, query):
        q = (body.get("q") or "").strip()
        if not q:
            return 400, {"error": "q 必填"}
        return svc().ask(q, library=body.get("library"))

    def scan(ctx, params, body, query):
        return svc().scan()

    def graph(ctx, params, body, query):
        return svc().graph(query.get("lib", "bagu"))

    def tree(ctx, params, body, query):
        return {"items": svc().tree(query.get("lib", "bagu"))}

    def ingest(ctx, params, body, query):
        """四入口：paste / url；上传文件走 multipart 由前端读文本后按 paste 走。"""
        way = body.get("way", "paste")
        lib = body.get("library", "mianjing")
        if way == "url":
            url = (body.get("url") or "").strip()
            if not url.startswith(("http://", "https://")):
                return 400, {"error": "url 不合法"}
            try:
                return svc().ingest_url(lib, url)
            except Exception as e:
                return 400, {"error": f"抓取失败：{e}"}
        title = (body.get("title") or "").strip()
        content = body.get("content") or ""
        if not title and not content.strip():
            return 400, {"error": "title/content 至少一项"}
        if not title:
            title = content.strip().splitlines()[0][:40]
        return svc().ingest(lib, title, content)

    def ingest_file(ctx, params, body, query):
        """上传文件：body {filename, content_b64}。"""
        import base64
        filename = body.get("filename", "")
        if not filename:
            return 400, {"error": "filename 必填"}
        try:
            data = base64.b64decode(body.get("content_b64", ""))
        except Exception:
            return 400, {"error": "content_b64 不合法"}
        return svc().ingest_file(body.get("library", "mianjing"), filename, data)

    def add_edge(ctx, params, body, query):
        return svc().add_manual_edge(body["src"], body["dst"])

    def remove_edge(ctx, params, body, query):
        return svc().remove_edge(body["src"], body["dst"])

    # ---- RAG 语义索引（F22） ----
    def rag_status(ctx, params, body, query):
        return svc().rag_status()

    def rag_index(ctx, params, body, query):
        return svc().rag_build()

    def clips(ctx, params, body, query):
        return {"items": svc().clips()}

    def add_clip(ctx, params, body, query):
        if not body.get("title"):
            return 400, {"error": "title 必填"}
        cid = svc().add_clip(body["title"], body.get("content", ""),
                             body.get("link", ""), body.get("tags", ""))
        return 201, {"id": cid}

    def del_clip(ctx, params, body, query):
        svc().delete_clip(int(params["id"]))
        return {"ok": True}

    def del_article(ctx, params, body, query):
        # v1.19：删除可写库文章（custom/mianjing/grad；bagu 只读拒删）
        path = (query.get("path") or (body or {}).get("path") or "").strip()
        if not path:
            return 400, {"error": "path 必填"}
        try:
            r = svc().delete_article(path)
        except ValueError as e:
            return 400, {"error": str(e)}
        return r or (404, {"error": "文章不存在"})

    router.get("/api/kb/search", search)
    router.get("/api/kb/article", article)
    router.post("/api/kb/ask", ask)
    router.post("/api/kb/scan", scan)
    router.get("/api/kb/graph", graph)
    router.get("/api/kb/tree", tree)
    router.post("/api/kb/ingest", ingest)
    router.post("/api/kb/ingest-file", ingest_file)
    router.post("/api/kb/edges", add_edge)
    router.delete("/api/kb/edges", remove_edge)
    router.get("/api/kb/clips", clips)
    router.post("/api/kb/clips", add_clip)
    router.delete("/api/kb/clips/{id}", del_clip)
    router.delete("/api/kb/article", del_article)   # v1.19
    router.get("/api/kb/rag/status", rag_status)
    router.post("/api/kb/rag/index", rag_index)
