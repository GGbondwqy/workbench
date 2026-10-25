# -*- coding: utf-8 -*-
"""v1.13 验收：AI 档案新增/删除。自清洁：临时档案全删，qwen 的 active 恢复。"""
import json
import urllib.request
import urllib.error

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


def names(cfg):
    return [p["name"] for p in cfg["ai"]["providers"]]


s, cfg0 = call("GET", "/api/config")
prev_active = cfg0["ai"]["active"]

print("== 1. 新增档案 ==")
s, r = call("PUT", "/api/config", {"ai": {"providers": [
    {"name": "v23-temp", "base_url": "https://example.com/v1", "model": "m1",
     "api_key": "sk-v23"}]}})
s, cfg = call("GET", "/api/config")
check("新增成功", "v23-temp" in names(cfg))
s, r = call("PUT", "/api/config", {"ai": {"providers": [
    {"name": "v23-temp", "base_url": "https://example2.com/v1"}]}})
s, cfg = call("GET", "/api/config")
check("同名合并不重复", names(cfg).count("v23-temp") == 1
      and next(p for p in cfg["ai"]["providers"] if p["name"] == "v23-temp")["base_url"]
      == "https://example2.com/v1")

print("== 2. 删除档案 ==")
s, r = call("PUT", "/api/config", {"ai": {"remove_provider": "v23-temp"}})
s, cfg = call("GET", "/api/config")
check("删除成功", "v23-temp" not in names(cfg))
s, r = call("PUT", "/api/config", {"ai": {"remove_provider": "v23-temp"}})
check("删除不存在→幂等", s == 200)

print("== 3. 删除使用中的档案→回落本地规则 ==")
call("PUT", "/api/config", {"ai": {"providers": [
    {"name": "v23-active", "base_url": "https://example.com/v1", "model": "m1",
     "api_key": "sk-v23"}]}})
call("PUT", "/api/config", {"ai": {"active": "v23-active"}})
s, cfg = call("GET", "/api/config")
check("临时档案已设为当前", cfg["ai"]["active"] == "v23-active")
call("PUT", "/api/config", {"ai": {"remove_provider": "v23-active"}})
s, cfg = call("GET", "/api/config")
check("档案已删且 active 置空", "v23-active" not in names(cfg)
      and cfg["ai"]["active"] is None)

print("== 4. 恢复用户配置 ==")
call("PUT", "/api/config", {"ai": {"active": prev_active}})
s, cfg = call("GET", "/api/config")
check("active 恢复", cfg["ai"]["active"] == prev_active)
check("预置只留 qwen", names(cfg) == ["qwen"])

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
