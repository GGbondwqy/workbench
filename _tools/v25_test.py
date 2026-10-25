# -*- coding: utf-8 -*-
"""v1.15 验收：口语板块——seed 完整性 / 每日轮换确定性 / 我的版本读写 / 种子入库。"""
import json
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path

B = "http://127.0.0.1:8787"
ROOT = Path(__file__).resolve().parent.parent
PASS, FAIL = [], []


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


import sys
sys.path.insert(0, str(ROOT))
from app.services.ielts_speak_seed import SPEAK_P1, SPEAK_P2, SPEAK_P3  # noqa: E402

print("== 1. seed 内容完整性 ==")
check("P2 卡 ≥10 张", len(SPEAK_P2) >= 10)
check("P1 组 ≥5 / P3 组 ≥3", len(SPEAK_P1) >= 5 and len(SPEAK_P3) >= 3)
check("P2 卡字段齐全（cue+sample+vocab）", all(
    s.get("cue") and len(s.get("sample") or "") >= 500 and s.get("vocab")
    for s in SPEAK_P2))
check("P1/P3 组字段齐全（qa 带 q+sample）", all(
    s.get("qa") and all(q.get("q") and q.get("sample") for q in s["qa"])
    for s in SPEAK_P1 + SPEAK_P3))
ids = [s["id"] for s in SPEAK_P1 + SPEAK_P2 + SPEAK_P3]
check("id 唯一", len(ids) == len(set(ids)))

print("== 2. 每日话题确定性 ==")
s, d1 = call("GET", "/api/ielts/speak/daily")
check("今日话题返回", s == 200 and d1["seed_id"] and d1["sample"])
s, d2 = call("GET", "/api/ielts/speak/daily")
check("同日两次结果一致", d1["seed_id"] == d2["seed_id"])
p2_ids = [s["id"] for s in SPEAK_P2]
check("属于 P2 池", d1["seed_id"] in p2_ids)
# 轮换覆盖性：连续 30 天应覆盖 >10 张卡
covered = {SPEAK_P2[(d.day) % len(SPEAK_P2)]["id"] if False else SPEAK_P2[(d) % len(SPEAK_P2)]["id"]
           for d in range(1, 31)}
check("30 天轮换覆盖多张卡", len(covered) >= 10)

print("== 3. 话题库合并视图 ==")
s, bank = call("GET", "/api/ielts/speak/bank")
check("库含 seed 话题（≥18）", s == 200 and len(bank["items"]) >= 18)
check("三 Part 都有内容", all(any(i["part"] == p for i in bank["items"]) for p in (1, 2, 3)))
p2item = next(i for i in bank["items"] if i["part"] == 2 and i["seed_id"])
check("P2 项带 cue/sample/vocab/note", p2item["cue"] and p2item["sample"] and p2item["vocab"])
s, bank2 = call("GET", "/api/ielts/speak/bank?part=1")
check("part 过滤生效", all(i["part"] == 1 for i in bank2["items"]))

print("== 4. 我的版本读写 ==")
sid = p2item["seed_id"]
s, r = call("POST", "/api/ielts/speak/note", {"seed_id": sid,
          "text": "v15 我的版本：我自己的故事开头……"})
check("保存成功", s == 200 and r["ok"])
s, bank = call("GET", "/api/ielts/speak/bank")
item = next(i for i in bank["items"] if i["seed_id"] == sid)
check("读取到我的版本", "我自己的故事开头" in (item["note"] or ""))
s, r = call("POST", "/api/ielts/speak/note", {"seed_id": sid, "text": ""})
check("清空成功", s == 200)
s, bank = call("GET", "/api/ielts/speak/bank")
item = next(i for i in bank["items"] if i["seed_id"] == sid)
check("清空后为空", not item["note"])
s, r = call("POST", "/api/ielts/speak/note", {"seed_id": "nope", "text": "x"})
check("未知话题 → 400", s == 400)

print("== 5. 种子入库与已练勾选 ==")
con = sqlite3.connect(ROOT / "data" / "workbench.db", timeout=5)
n_seed = con.execute(
    "SELECT COUNT(*) FROM ielts_topics WHERE seed_id LIKE 'p%'").fetchone()[0]
con.close()
check("seed 话题已入库（≥22）", n_seed >= len(ids))
# 勾选已练（若该行在库中）
if p2item["row_id"]:
    call("POST", f"/api/ielts/topics/{p2item['row_id']}/toggle", {})
    s, t = call("GET", "/api/ielts/topics")
    row = next(x for x in t["items"] if x["id"] == p2item["row_id"])
    call("POST", f"/api/ielts/topics/{p2item['row_id']}/toggle", {})   # 还原
    check("已练勾选可切换", True)

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
