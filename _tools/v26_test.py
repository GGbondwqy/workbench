# -*- coding: utf-8 -*-
"""v1.16 验收：口语录音（上传/列表/回放/删除/安全校验）+ 写作板块（seed/每日/我的作文）。"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

B = "http://127.0.0.1:8787"
ROOT = Path(__file__).resolve().parent.parent
PASS, FAIL = [], []


def call(method, path, body=None, ctype="application/json", raw=None):
    data = raw if raw is not None else (
        json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None)
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ct = r.headers.get("Content-Type", "")
            body = r.read()
            if "audio" in ct:
                return r.status, body, ct
            return r.status, json.loads(body.decode("utf-8")), ct
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8")), ""
        except Exception:
            return e.code, {}, ""


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


import sys
sys.path.insert(0, str(ROOT))
from app.services.ielts_write_seed import WRITE_T1, WRITE_T2  # noqa: E402

print("== 1. 写作 seed 完整性 ==")
check("T2 题 ≥8（sample ≥800 字符+structure+vocab）", len(WRITE_T2) >= 8 and all(
    len(s.get("sample") or "") >= 800 and s.get("structure") and s.get("vocab")
    for s in WRITE_T2))
check("T1 题 ≥4", len(WRITE_T1) >= 4 and all(
    s.get("sample") and s.get("structure") for s in WRITE_T1))
check("T1 id 不与 T2 重复", not {s["id"] for s in WRITE_T1} & {s["id"] for s in WRITE_T2})

print("== 2. 写作端点 ==")
s, r, _ = call("GET", "/api/ielts/write/daily")
check("每日任务 T1+T2", s == 200 and r["t1"]["task"] == 1 and r["t2"]["task"] == 2
      and r["t2"]["sample"])
s, r2, _ = call("GET", "/api/ielts/write/daily")
check("同日结果一致", r2["t2"]["id"] == r["t2"]["id"])
s, bank, _ = call("GET", "/api/ielts/write/bank?task=2")
check("题库 task 过滤", all(i["task"] == 2 for i in bank["items"]))
sid = "t2-education-online"
s, r, _ = call("POST", "/api/ielts/write/note", {"seed_id": sid,
               "text": "v16 test essay body with some words"})
check("保存我的作文", s == 200 and r["ok"])
s, bank, _ = call("GET", "/api/ielts/write/bank")
item = next(i for i in bank["items"] if i["id"] == sid)
check("读到我的作文", "v16 test essay" in (item["note"] or ""))
s, r, _ = call("POST", "/api/ielts/write/note", {"seed_id": sid, "text": ""})
check("清空成功", s == 200)
s, r, _ = call("POST", "/api/ielts/write/note", {"seed_id": "nope", "text": "x"})
check("未知题目 → 400", s == 400)

print("== 3. 口语录音（真实 webm 字节流） ==")
KEY = "p2-meal-enjoyed"
fake = b"\x1a\x45\xdf\xa3" + b"\x00" * 3000   # webm 魔数头 + payload
s, r, _ = call("POST", f"/api/ielts/speak/recording/{KEY}", raw=fake,
               ctype="audio/webm;codecs=opus")
check("上传成功（audio/* 透传）", s == 201 and r["name"].endswith(".webm"))
name = r["name"]
s, r, _ = call("POST", f"/api/ielts/speak/recording/{KEY}", raw=fake,
               ctype="audio/webm")
check("第二条可存（不同时间戳）", s == 201 and r["name"] != name)
time.sleep(1.1)
s, r, _ = call("POST", f"/api/ielts/speak/recording/{KEY}", raw=fake, ctype="audio/webm")
name2 = r["name"]
s, r, _ = call("GET", f"/api/ielts/speak/recording/{KEY}")
check("列表 ≥2 条（新在前）", len(r["items"]) >= 2 and r["items"][0]["name"] == name2)
s, body, ct = call("GET", f"/api/ielts/speak/recording/{KEY}/{name2}")
check("回放二进制直出（audio/webm）", s == 200 and body.startswith(b"\x1a\x45")
      and ct == "audio/webm")
s, r, _ = call("DELETE", f"/api/ielts/speak/recording/{KEY}/{name2}")
check("删除成功", s == 200)
s, r, _ = call("GET", f"/api/ielts/speak/recording/{KEY}")
check("删除后列表更新", all(x["name"] != name2 for x in r["items"]))

print("== 4. 录音安全与边界 ==")
s, r, _ = call("POST", "/api/ielts/speak/recording/..%5Cevil", raw=fake, ctype="audio/webm")
check("非法 key → 400", s == 400)
s, r, _ = call("POST", f"/api/ielts/speak/recording/{KEY}", raw=b"x", ctype="audio/webm")
check("太短录音 → 400", s == 400)
s, r, _ = call("POST", f"/api/ielts/speak/recording/{KEY}", raw=fake, ctype="text/html")
check("非音频类型 → 400", s == 400)
s, r, _ = call("GET", f"/api/ielts/speak/recording/{KEY}/..%2Fx.webm")
check("非法文件名 → 400/404", s in (400, 404))
# 清理测试录音
for x in call("GET", f"/api/ielts/speak/recording/{KEY}")[1]["items"]:
    call("DELETE", f"/api/ielts/speak/recording/{KEY}/{x['name']}")
s, r, _ = call("GET", f"/api/ielts/speak/recording/{KEY}")
check("测试录音已清", not r["items"])

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
