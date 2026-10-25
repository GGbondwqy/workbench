# -*- coding: utf-8 -*-
"""v1.8 版本验收：导师任务 / 组会记录删除链路。"""
import json
import urllib.request
from datetime import date, timedelta

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


# ========== 导师任务删除 ==========
s, r = call("POST", "/api/grad/advisor", {"content": "v18待办任务-勿留"})
aid1 = r.get("id")
s, r = call("POST", "/api/grad/advisor", {"content": "v18已转任务-勿留"})
aid2 = r.get("id")
check("导师·两条登记", s == 201 and aid1 and aid2)
call("POST", f"/api/grad/advisor/{aid2}/convert")  # 变为已转化态

s, r = call("DELETE", f"/api/grad/advisor/{aid1}")
s, r = call("GET", "/api/grad/advisor")
ids = [t["id"] for t in r["items"]]
check("导师·待处理可删", aid1 not in ids)
s, r = call("DELETE", f"/api/grad/advisor/{aid2}")
s, r = call("GET", "/api/grad/advisor")
check("导师·已转化记录可删", aid2 not in [t["id"] for t in r["items"]])

# ========== 组会记录删除 ==========
md = (date.today() - timedelta(days=1)).isoformat()
s, r = call("POST", "/api/grad/meetings", {"meet_date": md, "notes": "v18删除测试-勿留"})
mid = r.get("id")
check("组会·登记", s == 201 and mid)
s, r = call("DELETE", f"/api/grad/meetings/{mid}")
s, r = call("GET", "/api/grad/meetings")
check("组会·记录可删", mid not in [m["id"] for m in r["meetings"]])

# 清理转待办测试产生的任务
_s, _d = call("GET", "/api/dashboard")
for _t in _d["tasks"]:
    if "v18" in _t["title"]:
        call("DELETE", f"/api/tasks/{_t['id']}")

print(f"\n===== v1.8 专项：{len(PASS)} 通过 / {len(FAIL)} 失败 =====")
if FAIL:
    for f in FAIL:
        print("  FAIL:", f)
    raise SystemExit(1)
