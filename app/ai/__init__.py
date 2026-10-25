# -*- coding: utf-8 -*-
"""AI Provider 层：独立于业务，业务侧只通过 ctx.ai.chat() 调用。

设计（见 docs/ARCHITECTURE.md §6）：
- 统一 OpenAI 兼容格式 POST {base_url}/chat/completions
- 多档案（DeepSeek / Qwen / 中转站…），active 指定当前档案
- 未配置或调用失败 → chat() 返回 None，业务侧走本地规则降级
- status() 永不回传 api_key
- v1.10：list_models/ping 供设置页探测与连通测试；每次调用把响应里的
  token 用量经注入的 usage_sink 上抛（sink 由 bootstrap 接线到 usage 域，
  AI 层自身不落库、不 import 业务，保持独立）
"""
import json
import logging
import urllib.request

LOG = logging.getLogger("workbench.ai")


class OpenAICompatProvider:
    """OpenAI 兼容 API 适配器（DeepSeek / Qwen DashScope 兼容模式 / 各中转站通用）。"""

    def __init__(self, name: str, base_url: str, api_key: str, model: str, timeout: int = 60):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._usage_sink = None   # bootstrap 注入，见 AIRegistry.set_usage_sink

    def usable(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    # ---- v1.10：接入探测（地址/密钥/模型三验） ----
    def list_models(self) -> list[str]:
        """GET {base_url}/models → 模型 id 列表（升序）。地址或密钥不通时抛异常，由路由转 400。"""
        req = urllib.request.Request(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"}, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return sorted(m["id"] for m in data.get("data", []) if m.get("id"))

    def ping(self, model: str | None = None) -> tuple[int, str]:
        """1-token 极小对话，一次验证 地址+密钥+模型。返回 (耗时ms, 回复片段)。"""
        import time
        payload = {"model": model or self.model, "max_tokens": 1,
                   "messages": [{"role": "user", "content": "ping"}]}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"}, method="POST")
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ms = int((time.time() - t0) * 1000)
        reply = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
        return ms, str(reply)[:60]

    def chat(self, messages: list[dict], temperature: float = 0.7,
             max_tokens: int | None = None, feature: str = "其他") -> str:
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self._report(feature, "chat", self.model, data.get("usage") or {})
        return data["choices"][0]["message"]["content"]

    def _report(self, feature: str, kind: str, model: str, usage: dict):
        if not usage:
            return
        try:
            if self._usage_sink is not None:
                # 缓存命中两种上游风格：OpenAI 系嵌套 prompt_tokens_details.cached_tokens
                # 优先，兜底 DeepSeek 系顶层 prompt_cache_hit_tokens；均无记 0
                cached = 0
                details = usage.get("prompt_tokens_details") or {}
                if isinstance(details, dict) and details.get("cached_tokens"):
                    cached = int(details["cached_tokens"])
                elif usage.get("prompt_cache_hit_tokens"):
                    cached = int(usage["prompt_cache_hit_tokens"])
                self._usage_sink(feature=feature, provider=self.name, model=model,
                                 kind=kind, usage={
                                     "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                                     "completion_tokens": int(usage.get("completion_tokens") or 0),
                                     "total_tokens": int(usage.get("total_tokens") or 0),
                                     "cached_tokens": cached})
        except Exception:
            LOG.exception("usage 记账失败（不影响业务调用）")


class AIRegistry:
    DEFAULT_EMBEDDING_MODEL = "qwen3.7-text-embedding-flash"

    def __init__(self, ai_config: dict):
        self._active_name = ai_config.get("active")
        self._embedding_model = (ai_config.get("embedding") or {}).get(
            "model") or self.DEFAULT_EMBEDDING_MODEL
        self._providers: dict[str, OpenAICompatProvider] = {}
        for p in ai_config.get("providers", []):
            if not p.get("enabled", True):
                continue
            self._providers[p["name"]] = OpenAICompatProvider(
                name=p["name"], base_url=p.get("base_url", ""),
                api_key=p.get("api_key", ""), model=p.get("model", ""))

    # ---- v1.10：记账 sink 注入（bootstrap → usage 域，AI 层不 import 业务） ----
    def set_usage_sink(self, sink) -> None:
        for prov in self._providers.values():
            prov._usage_sink = sink

    def refresh(self, ai_config: dict) -> None:
        """配置热更新后重建 providers（保持已注入的 usage_sink）。"""
        sink_holder = next(iter(self._providers.values()), None)
        old_sink = getattr(sink_holder, "_usage_sink", None) if sink_holder else None
        self.__init__(ai_config)
        if old_sink is not None:
            self.set_usage_sink(old_sink)

    def probe(self, base_url: str, api_key: str, model: str = "") -> OpenAICompatProvider:
        """临时 provider（设置页探测/测试用，不进档案）。"""
        return OpenAICompatProvider(name="(probe)", base_url=base_url,
                                    api_key=api_key, model=model)

    def _active(self) -> OpenAICompatProvider | None:
        p = self._providers.get(self._active_name)
        if p is None or not p.usable():
            return None
        return p

    def chat(self, messages: list[dict], **kw) -> str | None:
        """无可用 Provider 或调用失败时返回 None（业务侧降级）。"""
        provider = self._active()
        if provider is None:
            return None
        try:
            return provider.chat(messages, **kw)
        except Exception:
            LOG.exception("AI 调用失败 provider=%s", provider.name)
            return None

    def embedding_model(self) -> str:
        return self._embedding_model

    def embed(self, texts: list[str], model: str | None = None,
              batch: int = 10, feature: str = "语义嵌入") -> list[list[float]] | None:
        """批量语义向量（OpenAI 兼容 /embeddings）。失败返回 None，业务侧退回关键词检索。
        返回顺序与输入一致；调用方自行归一化。中转站大响应易断流 → 小批 + 退避重试。"""
        provider = self._active()
        if provider is None or not texts:
            return None
        model = model or self._embedding_model
        import time
        out: list[list[float]] = []
        try:
            for i in range(0, len(texts), batch):
                payload = {"model": model, "input": texts[i:i + batch]}
                last_err = None
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(
                            f"{provider.base_url}/embeddings",
                            data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type": "application/json",
                                     "Authorization": f"Bearer {provider.api_key}"},
                            method="POST")
                        with urllib.request.urlopen(req, timeout=90) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                        rows = sorted(data["data"], key=lambda d: d.get("index", 0))
                        out.extend(r["embedding"] for r in rows)
                        provider._report(feature, "embed", model, data.get("usage") or {})
                        last_err = None
                        break
                    except Exception as e:  # 断流/超时 → 退避重试本批
                        last_err = e
                        time.sleep(1.5 * (attempt + 1))
                if last_err is not None:
                    raise last_err
                time.sleep(0.15)   # 批间限速，降低网关压力
            return out
        except Exception:
            LOG.exception("embeddings 调用失败 provider=%s model=%s",
                          provider.name, model)
            return None

    def status(self) -> dict:
        p = self._active()
        return {
            "configured": p is not None,
            "active": p.name if p else self._active_name,
            "providers": [
                {"name": name, "model": prov.model, "usable": prov.usable()}
                for name, prov in sorted(self._providers.items())
            ],
        }
