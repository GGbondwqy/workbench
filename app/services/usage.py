# -*- coding: utf-8 -*-
"""AI 用量域（DESIGN v2.8）：本地自动记账 + 价格折算。

- 数据来源：AI 层每次调用把响应里的 usage 经注入的 sink 送到 record()（见 post_migrate/attach）；
  AI 层自身不落库——接线在组合根（bootstrap/put_config），互不 import（红线）。
- 只存 token 数，不存折算价：查询时按当前价格表算钱，改单价即全量重算。
- 价格：内置常见模型参考价（每 1M token 元，输入/输出两档）+ settings 域 ai_prices 用户覆盖；
  未命中的模型 priced=False（花费计 0，页面上标"未定价"提示去改单价）。
"""
from app.core.registry import AppContext
from app.core.timeutil import now, today

MIGRATIONS = [
    ("0021_ai_usage", """
        CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,               -- 'YYYY-MM-DD HH:MM:SS'
            provider TEXT DEFAULT '',
            model TEXT NOT NULL,
            kind TEXT NOT NULL,             -- chat / embed
            feature TEXT DEFAULT '其他',      -- 知识问答/每日建议/学习卡片/语义嵌入…
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_ai_usage_day ON ai_usage(ts);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_model ON ai_usage(model);
    """),
    # v1.12：缓存命中 token（ALTER 兼容新老库；上游不返回时为 0=输入全价）
    ("0022_ai_usage_cached", """
        ALTER TABLE ai_usage ADD COLUMN cached_tokens INTEGER DEFAULT 0;
    """),
]

# 内置参考价（元 / 每百万 token：输入, 输出, 缓存命中输入）。参考官方刊例，
# 中转站可能不同——页面上可改。缓存命中价：DeepSeek 官方为输入的 25%，其余默认 50%。
# 匹配规则：覆盖表精确命中 > 规则子串匹配（长键优先，忽略大小写）。
PRICE_RULES = [
    ("deepseek-reasoner", 4.0, 16.0, 1.0),
    ("deepseek-r", 4.0, 16.0, 1.0),
    ("deepseek", 2.0, 8.0, 0.5),
    ("qwen-max", 2.4, 9.6, 1.2),
    ("qwen-plus", 0.8, 2.0, 0.4),
    ("qwen-turbo", 0.3, 0.6, 0.15),
    ("qwen", 0.5, 1.5, 0.25),
    ("text-embedding", 0.5, 0.0, 0.25),
    ("embedding", 0.5, 0.0, 0.25),
    ("glm-4-flash", 0.1, 0.1, 0.05),
    ("glm", 1.0, 3.0, 0.5),
    ("gpt-4o-mini", 1.1, 4.4, 0.55),
    ("gpt-4.1", 2.0, 8.0, 1.0),
    ("gpt-4o", 18.0, 72.0, 9.0),
    ("gpt", 2.0, 8.0, 1.0),
    ("o4-mini", 1.1, 4.4, 0.55),
    ("o3", 14.5, 58.0, 7.25),
    ("claude-haiku", 6.0, 29.0, 0.6),
    ("claude", 22.0, 108.0, 2.2),
    ("gemini-flash", 2.2, 18.0, 1.1),
    ("gemini", 9.0, 72.0, 4.5),
]
PRICE_RULES.sort(key=lambda r: -len(r[0]))


class UsageService:
    name = "usage_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 记账入口（AI 层 sink 指到这里） ----
    def record(self, feature, provider, model, kind, usage):
        cached = int(usage.get("cached_tokens") or 0)
        pin = int(usage.get("prompt_tokens") or 0)
        # 上游异常时 cached 不可能超过 prompt，钳制防脏数据把花费算负
        self._ctx.db.execute(
            "INSERT INTO ai_usage(ts, provider, model, kind, feature,"
            " prompt_tokens, completion_tokens, total_tokens, cached_tokens)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (now(), provider, model, kind, feature or "其他",
             pin,
             usage.get("completion_tokens") or 0,
             usage.get("total_tokens") or 0,
             min(cached, pin)))

    def attach(self, ctx):
        """把 record 注入 AI 层（post_migrate 与配置热更新后都调）。"""
        if getattr(ctx, "ai", None) is not None:
            ctx.ai.set_usage_sink(self.record)

    # ---- 价格 ----
    def _overrides(self) -> dict:
        ov = self._ctx.services.get("settings_service").get("ai_prices")
        return ov if isinstance(ov, dict) else {}

    def resolve_price(self, model: str):
        """→ (输入价, 输出价, 缓存命中价, 是否定价)。覆盖精确命中优先，其次规则子串。
        旧覆盖 {in,out} 缺 hit 时按 0.5×in 补（v1.12 兼容）。"""
        ov = self._overrides().get(model or "")
        if isinstance(ov, dict) and ov.get("in") is not None:
            pin, pout = float(ov["in"]), float(ov.get("out") or 0)
            hit = ov.get("hit")
            return pin, pout, float(hit) if hit is not None else pin * 0.5, True
        m = (model or "").lower()
        for key, pin, pout, phit in PRICE_RULES:
            if key in m:
                return pin, pout, phit, True
        return 0.0, 0.0, 0.0, False

    def set_price(self, model: str, price_in, price_out, price_hit=None):
        ov = self._overrides()
        entry = {"in": float(price_in), "out": float(price_out or 0)}
        if price_hit is not None:
            entry["hit"] = max(0.0, float(price_hit))
        ov[model] = entry
        self._ctx.services.get("settings_service").set("ai_prices", ov)
        return ov

    def used_models(self):
        rows = self._ctx.db.query(
            "SELECT model, COUNT(*) n, SUM(prompt_tokens) pin, SUM(completion_tokens) pout,"
            " SUM(cached_tokens) cached"
            " FROM ai_usage GROUP BY model ORDER BY SUM(total_tokens) DESC")
        out = []
        for r in rows:
            pin, pout, phit, priced = self.resolve_price(r["model"])
            out.append({"model": r["model"], "calls": r["n"],
                        "prompt_tokens": r["pin"] or 0, "completion_tokens": r["pout"] or 0,
                        "cached_tokens": r["cached"] or 0,
                        "price_in": pin, "price_out": pout, "price_hit": phit,
                        "priced": priced})
        return out

    # ---- 汇总 ----
    def summary(self, days: int = 30):
        db = self._ctx.db
        t = today()                       # 'YYYY-MM-DD'
        month = t[:7]

        def cost_of(pin, pout, cached, model):
            """未命中输入×全价 + 缓存命中×折扣价 + 输出×输出价（v1.12）。"""
            i, o, h, _ = self.resolve_price(model)
            miss = max(0, pin - min(cached, pin))
            return (miss * i + min(cached, pin) * h + pout * o) / 1_000_000

        def scope_rows(where, args=()):
            """按模型聚合某时间范围内的量并折算花费。"""
            rows = db.query(
                f"SELECT model, COUNT(*) n, SUM(prompt_tokens) pin,"
                f" SUM(completion_tokens) pout, SUM(cached_tokens) cached"
                f" FROM ai_usage {where} GROUP BY model", args)
            calls = sum(r["n"] for r in rows)
            pin = sum(r["pin"] or 0 for r in rows)
            pout = sum(r["pout"] or 0 for r in rows)
            cached = sum(r["cached"] or 0 for r in rows)
            cost = round(sum(cost_of(r["pin"] or 0, r["pout"] or 0, r["cached"] or 0,
                                     r["model"]) for r in rows), 6)
            return {"calls": calls, "prompt_tokens": pin, "completion_tokens": pout,
                    "cached_tokens": cached, "cost": cost}

        today_r = scope_rows("WHERE ts LIKE ?", (f"{t} %",))
        month_r = scope_rows("WHERE substr(ts,1,7)=?", (month,))

        # 逐日趋势（近 N 天，补零）
        from datetime import date, timedelta
        d0 = date.today() - timedelta(days=days - 1)
        series = []
        for i in range(days):
            d = (d0 + timedelta(days=i)).isoformat()
            series.append({"day": d, **scope_rows("WHERE substr(ts,1,10)=?", (d,))})

        # 按模型
        models = []
        for r in db.query(
                "SELECT model, provider, COUNT(*) n, SUM(prompt_tokens) pin,"
                " SUM(completion_tokens) pout, SUM(cached_tokens) cached, SUM(total_tokens) tt"
                " FROM ai_usage GROUP BY model ORDER BY tt DESC"):
            models.append({"model": r["model"], "provider": r["provider"], "calls": r["n"],
                           "prompt_tokens": r["pin"] or 0, "completion_tokens": r["pout"] or 0,
                           "cached_tokens": r["cached"] or 0,
                           "cost": round(cost_of(r["pin"] or 0, r["pout"] or 0,
                                                 r["cached"] or 0, r["model"]), 6),
                           "priced": self.resolve_price(r["model"])[3]})

        # 按功能（花费用 功能×模型 交叉折算）
        features = []
        for r in db.query(
                "SELECT feature, COUNT(*) n, SUM(prompt_tokens) pin,"
                " SUM(completion_tokens) pout, SUM(cached_tokens) cached, SUM(total_tokens) tt"
                " FROM ai_usage GROUP BY feature ORDER BY tt DESC"):
            features.append({"feature": r["feature"], "calls": r["n"],
                             "prompt_tokens": r["pin"] or 0,
                             "completion_tokens": r["pout"] or 0,
                             "cached_tokens": r["cached"] or 0,
                             "cost": 0.0})
        for r in db.query(
                "SELECT feature, model, SUM(prompt_tokens) pin, SUM(completion_tokens) pout,"
                " SUM(cached_tokens) cached FROM ai_usage GROUP BY feature, model"):
            for f in features:
                if f["feature"] == r["feature"]:
                    f["cost"] = round(f["cost"] +
                                      cost_of(r["pin"] or 0, r["pout"] or 0,
                                              r["cached"] or 0, r["model"]), 6)

        return {
            "today": today_r,
            "month": month_r,
            "all": {"calls": sum(m["calls"] for m in models),
                    "cost": round(sum(m["cost"] for m in models), 6)},
            "trend": series,
            "by_model": models,
            "by_feature": features,
        }


def register(ctx: AppContext):
    svc = UsageService(ctx)
    ctx.services.register(UsageService.name, svc)


def post_migrate(ctx: AppContext):
    """迁移完成后接线：AI 层每次调用的 usage 记到 ai_usage 表。"""
    svc = ctx.services.try_get(UsageService.name)
    if svc:
        svc.attach(ctx)
