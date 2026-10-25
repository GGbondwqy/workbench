# -*- coding: utf-8 -*-
"""配置路由：AI 档案 / 知识库路径 热更新（写 data/config.json 并即时生效）。"""
from app.core.registry import AppContext
from app.core import config as config_mod
from app import ai as ai_pkg


def register_routes(router, ctx):
    def get_config(ctx: AppContext, params, body, query):
        # 永不回传密钥本体，只回传是否已填
        cfg = ctx.config
        providers = [
            {"name": p.get("name"), "base_url": p.get("base_url", ""),
             "model": p.get("model", ""),
             "has_key": bool(p.get("api_key")), "enabled": p.get("enabled", True)}
            for p in cfg.get("ai", {}).get("providers", [])
        ]
        return {
            "ai": {"active": cfg.get("ai", {}).get("active"), "providers": providers,
                   "embedding": (cfg.get("ai", {}).get("embedding") or {}).get(
                       "model", ai_pkg.AIRegistry.DEFAULT_EMBEDDING_MODEL)},
            "kb": {"path": cfg.get("kb", {}).get("path")},
            "leetcode": {
                "username": (cfg.get("leetcode", {}) or {}).get("username", ""),
                "has_cookie": bool((cfg.get("leetcode", {}) or {}).get("cookie")),
                "folder": (cfg.get("leetcode", {}) or {}).get("folder", ""),
            },
        }

    def put_config(ctx: AppContext, params, body, query):
        """可更新：ai.active / ai.providers[i].* / ai.remove_provider / ai.embedding.model
        （api_key 明文传入后只存本地）/ kb.path"""
        cfg = ctx.config
        ai_patch = body.get("ai") or {}
        # v1.13：物理删除档案（密钥随之清除）；active 指向被删档案则回落本地规则
        remove = ai_patch.get("remove_provider")
        if remove:
            cfg.setdefault("ai", {})["providers"] = [
                p for p in cfg["ai"].get("providers", []) if p.get("name") != remove]
            if cfg["ai"].get("active") == remove:
                cfg["ai"]["active"] = None
        if "active" in ai_patch:
            cfg.setdefault("ai", {})["active"] = ai_patch["active"]
        emb_model = (ai_patch.get("embedding") or {}).get("model")
        if emb_model:
            cfg.setdefault("ai", {}).setdefault("embedding", {})["model"] = emb_model
        for p_in in ai_patch.get("providers", []):
            name = p_in.get("name")
            target = next((p for p in cfg.setdefault("ai", {}).get("providers", [])
                           if p.get("name") == name), None)
            if target is None:
                target = {"name": name}
                cfg["ai"].setdefault("providers", []).append(target)
            for k in ("base_url", "model", "enabled"):
                if k in p_in:
                    target[k] = p_in[k]
            if p_in.get("api_key"):
                target["api_key"] = p_in["api_key"]
        if "kb" in body:
            cfg["kb"] = {"path": body["kb"].get("path") or None}
        if "leetcode" in body:
            lc = body["leetcode"]
            cur = cfg.get("leetcode", {})
            cur.update({k: v for k, v in lc.items() if k in ("username", "cookie", "folder")})
            cfg["leetcode"] = cur
        config_mod.save_config(ctx.data_dir, cfg)
        # AI 档案热重建（保住已注入的 usage 记账 sink）；kb 路径生效需要重扫
        ctx.ai.refresh(cfg.get("ai", {}))
        kb_svc = ctx.services.try_get("kb_service")
        kb_rescan = kb_svc.scan() if kb_svc else None
        return {"ok": True, "ai": ctx.ai.status(), "kb_rescan": kb_rescan}

    # ---- v1.10：模型列表拉取 + 连通测试（设置页用；不回传任何密钥） ----
    def _probe_args(ctx: AppContext, body):
        """优先用请求里的 base_url/key；key 未传时可按档案名取已存密钥。"""
        base_url = (body.get("base_url") or "").strip()
        key = (body.get("api_key") or "").strip()
        name = (body.get("provider_name") or "").strip()
        if not base_url or not key:
            stored = next((p for p in ctx.config.get("ai", {}).get("providers", [])
                           if p.get("name") == name), None)
            if stored:
                base_url = base_url or stored.get("base_url", "")
                key = key or stored.get("api_key", "")
        return base_url, key

    def ai_models(ctx: AppContext, params, body, query):
        base_url, key = _probe_args(ctx, body)
        if not base_url or not key:
            return 400, {"error": "需要 base_url 和 API Key（或指定已存档案名）"}
        try:
            return {"models": ctx.ai.probe(base_url, key).list_models()}
        except Exception as e:
            return 400, {"error": f"拉取失败：{_friendly(e)}"}

    def ai_test(ctx: AppContext, params, body, query):
        base_url, key = _probe_args(ctx, body)
        model = (body.get("model") or "").strip()
        if not base_url or not key:
            return 400, {"error": "需要 base_url 和 API Key（或指定已存档案名）"}
        if not model:
            return 400, {"error": "请先选择模型"}
        try:
            ms, reply = ctx.ai.probe(base_url, key).ping(model)
            return {"ok": True, "latency_ms": ms, "reply": reply}
        except Exception as e:
            return 400, {"error": f"不通：{_friendly(e)}"}

    def _friendly(e: Exception) -> str:
        import urllib.error
        if isinstance(e, urllib.error.HTTPError):
            hint = {401: "密钥无效或已过期", 403: "无权限（密钥或分组不对）",
                    404: "地址不对或无此模型", 429: "请求太频繁/额度不足"}.get(e.code, "")
            return f"HTTP {e.code}{('：' + hint) if hint else ''}"
        if isinstance(e, urllib.error.URLError) and "timed out" in str(e).lower():
            return "连接超时（地址不对或网络不通）"
        return str(e)[:120]

    router.get("/api/config", get_config)
    router.put("/api/config", put_config)
    router.post("/api/ai/models", ai_models)
    router.post("/api/ai/test", ai_test)
