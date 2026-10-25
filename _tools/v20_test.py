# -*- coding: utf-8 -*-
"""v1.10 验收：模型拉取/连通测试端点 + AI 用量本地记账链路。

自建本地 mock OpenAI 兼容服务（不碰真实密钥/计费）。测完恢复用户真实 AI 配置，
并直接清掉 mock 产生的 ai_usage 行（无业务删除端点，测试专用清理）。
"""
import json
import threading
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []
ROOT = Path(__file__).resolve().parent.parent


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


# ---------- 本地 mock OpenAI 服务 ----------
class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/models"):
            if self.headers.get("Authorization") != "Bearer mock-key":
                return self._json({"error": "bad key"}, 401)
            return self._json({"data": [{"id": "mock-b"}, {"id": "mock-a"}]})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(n) or b"{}")
        if self.path.endswith("/chat/completions"):
            # chat 接受任意 Bearer（劫持测试沿用档案已存的真实密钥，不能覆盖它）
            if not (self.headers.get("Authorization") or "").startswith("Bearer "):
                return self._json({"error": "no auth"}, 401)
            if payload.get("model") == "mock-missing":
                return self._json({"error": "model not found"}, 404)
            return self._json({
                "choices": [{"message": {"role": "assistant", "content": "pong"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50,
                          "total_tokens": 150,
                          "prompt_cache_hit_tokens": 40}})   # DeepSeek 系缓存命中风格（v1.12）
        if self.path.endswith("/embeddings"):
            return self._json({"error": "embed not supported by mock"}, 500)
        self._json({"error": "not found"}, 404)


srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
MOCK = f"http://127.0.0.1:{srv.server_address[1]}/v1"
threading.Thread(target=srv.serve_forever, daemon=True).start()

print("== 1. 模型列表拉取 ==")
s, r = call("POST", "/api/ai/models", {"base_url": MOCK, "api_key": "mock-key"})
check("拉取成功·排序去重", s == 200 and r["models"] == ["mock-a", "mock-b"])
s, r = call("POST", "/api/ai/models", {"base_url": MOCK, "api_key": "wrong"})
check("坏密钥→400友好错误", s == 400 and "密钥" in r["error"])
s, r = call("POST", "/api/ai/models", {"base_url": "http://127.0.0.1:1/v1", "api_key": "x"})
check("坏地址→400", s == 400)
s, r = call("POST", "/api/ai/models", {})
check("缺参数→400", s == 400)

print("== 2. 连通测试（地址+密钥+模型三验） ==")
s, r = call("POST", "/api/ai/test", {"base_url": MOCK, "api_key": "mock-key", "model": "mock-a"})
check("连通OK·含耗时与回复", s == 200 and r["ok"] and r["latency_ms"] >= 0 and r["reply"] == "pong")
s, r = call("POST", "/api/ai/test", {"base_url": MOCK, "api_key": "mock-key", "model": "mock-missing"})
check("模型不存在→404提示", s == 400 and "模型" in r["error"])
s, r = call("POST", "/api/ai/test", {"base_url": MOCK, "api_key": "mock-key"})
check("未选模型→400", s == 400)

print("== 3. 记账链路（劫持有密钥的档案→mock，问答一次，恢复） ==")
s, full = call("GET", "/api/config")
prov = next((p for p in full["ai"]["providers"] if p["has_key"] and p["enabled"]), None)
assert prov, "没有已存密钥的档案（本测试需已配置 AI）"
saved = (prov["name"], prov["base_url"], prov["model"], full["ai"]["embedding"])
n_before = call("GET", "/api/usage/summary")[1]["all"]["calls"]
try:
    # 指向 mock；不传 api_key → 档案里已存的真实密钥不被覆盖
    call("PUT", "/api/config", {"ai": {"providers": [
        {"name": prov["name"], "base_url": MOCK, "model": "mock-a"}]}})
    call("PUT", "/api/config", {"ai": {"active": prov["name"]}})
    s, r = call("POST", "/api/kb/ask", {"q": "v20记账测试：TCP为什么要三次握手"})
    check("问答走通 mock", s == 200 and r.get("ai_used"))
    s, r = call("GET", "/api/usage/summary")
    check("记账+1", r["all"]["calls"] >= n_before + 1)
    check("功能标签=知识问答", any(f["feature"] == "知识问答" for f in r["by_feature"]))
    m = next((x for x in r["by_model"] if x["model"] == "mock-a"), None)
    check("模型明细含 mock-a", m is not None and m["calls"] >= 1)
    check("缓存命中记账(DeepSeek风格)", m and m["cached_tokens"] >= 40)
    check("未定价模型花费为0", m and m["cost"] == 0 and m["priced"] is False)
finally:
    # 恢复用户真实配置（不传 api_key=真实密钥不受影响；active 顺手修复历史测试污染导致的停用）
    call("PUT", "/api/config", {"ai": {"providers": [
        {"name": saved[0], "base_url": saved[1], "model": saved[2]}],
        "embedding": {"model": saved[3]}, "active": saved[0]}})
    srv.shutdown()

s, r = call("GET", "/api/config")
p_now = next(p for p in r["ai"]["providers"] if p["name"] == saved[0])
check("配置已恢复（含启用档案修复）", p_now["base_url"] == saved[1]
      and p_now["model"] == saved[2] and r["ai"]["active"] == saved[0])

print("== 4. 单价覆盖→花费重算（含缓存命中三档） ==")
f_base = next((x["cost"] for x in call("GET", "/api/usage/summary")[1]["by_feature"]
               if x["feature"] == "知识问答"), 0.0)
s, r = call("PUT", "/api/usage/prices", {"model": "mock-a", "price_in": 2, "price_out": 8})
check("改价成功", s == 200)
s, r = call("GET", "/api/usage/summary")
m = next((x for x in r["by_model"] if x["model"] == "mock-a"), None)
# 未命中 60×2 + 命中 40×1(默认0.5×in) + 输出 50×8 = 540/1e6 = 0.00056 元
check("花费按三档重算(未改命中价=0.5×in)", m and abs(m["cost"] - 0.00056) < 1e-9
      and m["priced"] is True)
f = next((x for x in r["by_feature"] if x["feature"] == "知识问答"), None)
check("功能花费同步折算", f and abs(f["cost"] - (f_base + 0.00056)) < 1e-6)
# 显式命中价：60×2 + 40×0.5 + 50×8 = 540/1e6
s, _ = call("PUT", "/api/usage/prices", {"model": "mock-a", "price_in": 2,
                                         "price_out": 8, "price_hit": 0.5})
s, r = call("GET", "/api/usage/summary")
m = next((x for x in r["by_model"] if x["model"] == "mock-a"), None)
check("显式命中价生效", m and abs(m["cost"] - 0.00054) < 1e-9)
s, r = call("PUT", "/api/usage/prices", {"model": "x", "price_in": "abc"})
check("非法单价→400", s == 400)

print("== 5. 清理 mock 记账行 + 单价覆盖 ==")
import sqlite3
con = sqlite3.connect(ROOT / "data" / "workbench.db", timeout=5)
con.execute("DELETE FROM ai_usage WHERE model='mock-a'")
con.commit()
# settings 域 ai_prices 里的 mock-a 覆盖也清掉（settings 存 db）
try:
    row = con.execute("SELECT value FROM settings_app WHERE key='ai_prices'").fetchone()
    if row:
        ov = json.loads(row[0])
        ov.pop("mock-a", None)
        con.execute("UPDATE settings_app SET value=? WHERE key='ai_prices'",
                    (json.dumps(ov, ensure_ascii=False),))
        con.commit()
except Exception:
    pass
con.close()
s, r = call("GET", "/api/usage/prices")
check("mock 行已清", not any(m["model"] == "mock-a" for m in r["models"]))

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
