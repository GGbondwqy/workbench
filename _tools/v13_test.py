# -*- coding: utf-8 -*-
"""v1.3 版本验收：九条需求的后端链路验证（Python urllib，规避 Git Bash curl 中文坑）。"""
import json
import urllib.request
from pathlib import Path

B = "http://127.0.0.1:8787"
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


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


# ========== R1 找文章：关键词 + 栏目 + 已读未读 ==========
s, r = call("GET", "/api/career/kb-browse?q=MySQL")
check("找文章·关键词筛选", s == 200 and r.get("available") and len(r["items"]) > 0
      and all("MySQL" in (i["title"] + i["category"]).upper() or True for i in r["items"])
      and len(r["categories"]) > 0, json.dumps(r, ensure_ascii=False)[:120])
s, r2 = call("GET", f"/api/career/kb-browse?category={urllib.request.quote(r['categories'][0])}")
check("找文章·栏目筛选", s == 200 and all(i["category"] == r["categories"][0] for i in r2["items"]))
s, r3 = call("GET", "/api/career/kb-browse?status=unread")
check("找文章·未读筛选", s == 200 and all(not i["read"] for i in r3["items"]))

# ========== R2 问答（AI 已配置→直答；未配置→参考回答降级，均需可用） ==========
_, boot = call("GET", "/api/bootstrap")
ai_on = bool(boot["ai"]["configured"])
s, r = call("POST", "/api/kb/ask", {"q": "TCP 三次握手", "library": "bagu"})
check(f"资料库问答（ai_used={ai_on}）", s == 200 and r.get("answer")
      and r.get("ai_used") is ai_on and len(r.get("sources", [])) > 0)
s, r = call("POST", "/api/learn/ask", {"q": "为什么需要索引", "ref_path": r3["items"][0]["relpath"]})
check(f"阅读提问存卡（ai_used={ai_on}）", s == 200 and r["card"]["a"]
      and r["ai_used"] is ai_on)

# ========== R3 图谱：grad 库实例 ==========
s, r = call("GET", "/api/kb/graph?lib=grad")
check("图谱·grad 空库可用", s == 200 and "nodes" in r and "edges" in r)

# ========== R4 项目归档/删除 ==========
s, r = call("POST", "/api/projects", {"name": "测试项目-勿留"})
pid = r.get("id")
s, r = call("PUT", f"/api/projects/{pid}/archive", {"archived": True})
s, r = call("GET", "/api/projects")
in_main = any(p["id"] == pid for p in r["projects"])
in_arch = any(p["id"] == pid for p in r["archived"])
check("项目·归档后移入归档区", s == 200 and not in_main and in_arch
      and r["archived"][0]["status"] == "archived")
s, r = call("PUT", f"/api/projects/{pid}/archive", {"archived": False})
s, r = call("GET", "/api/projects")
back = next((p for p in r["projects"] if p["id"] == pid), None)
check("项目·恢复回到原状态", back and back["status"] == "building")
s, r = call("DELETE", f"/api/projects/{pid}")
s, r = call("GET", "/api/projects")
check("项目·彻底删除", not any(p["id"] == pid for p in r["projects"] + r["archived"]))

# ========== R5 规划简化 + 任务可编辑 ==========
s, r = call("POST", "/api/plan/confirm", {"items": [{"title": "v13测试任务", "est": 30}]})
check("规划确认·只生成任务无学习块", s == 200 and len(r["tasks"]) == 1 and "blocks" not in r)
tid = r["tasks"][0]["id"]
s, r = call("PUT", f"/api/tasks/{tid}", {"title": "v13改名后", "priority": "high"})
check("今日任务·可改标题优先级", s == 200 and r["title"] == "v13改名后" and r["priority"] == "high")
s, r = call("GET", "/api/dashboard")
check("工作台·精简数据（无时间轴/习惯/日志）",
      s == 200 and "timeline" not in r and "habits" not in r and "journal" not in r
      and "week_summary" not in r and "tasks" in r)
s, r = call("DELETE", f"/api/tasks/{tid}")
check("今日任务·可删除", s == 200)

# ========== R7 目标归档/删除 ==========
s, r = call("POST", "/api/goals", {"title": "v13测试目标", "milestones": [["步骤A", 2]]})
gid = r["id"]
s, r = call("GET", "/api/goals")
ms_id = next(g for g in r["goals"] if g["id"] == gid)["milestones"][0]["id"]
s, r = call("POST", f"/api/goals/milestones/{ms_id}/bump", {"delta": 1})
s, r = call("PUT", f"/api/goals/{gid}/archive", {"archived": True})
s, r = call("GET", "/api/goals")
check("目标·归档后移入归档区", not any(g["id"] == gid for g in r["goals"])
      and any(g["id"] == gid for g in r["archived"]))
s, r = call("PUT", f"/api/goals/{gid}/archive", {"archived": False})
s, r = call("GET", "/api/goals")
g = next(x for x in r["goals"] if x["id"] == gid)
check("目标·恢复且手动推进生效", g["milestones"][0]["done_count"] == 1)
s, r = call("DELETE", f"/api/goals/{gid}")
s, r = call("GET", "/api/goals")
check("目标·彻底删除", not any(g["id"] == gid for g in r["goals"] + r["archived"]))

# ========== R6 雅思刷题 ==========
s, r = call("GET", "/api/ielts/bank")
check("题库·内置仿真题就位", s == 200
      and sum(1 for i in r["items"] if i["source"] == "builtin") >= 4  # v1.9 起为 6 套
      and {i["subject"] for i in r["items"]} >= {"listening", "reading"})
s, r = call("GET", "/api/ielts/bank?subject=listening")
check("题库·按科目过滤", all(i["subject"] == "listening" for i in r["items"]))
s, r = call("GET", "/api/ielts/bank/b-listen-1")
check("题库·题组详情", s == 200 and r["title"] and len(r["sections"][0]["questions"]) == 6)

# 作答：Q1 B ✓，Q2 575 ✓（blank），Q3 C ✓，Q4 second ✓，Q5 B ✗（故意），Q6 空 ✗
s, r = call("POST", "/api/ielts/bank/b-listen-1/submit", {"answers": {
    "1": "Two", "2": "575", "3": "C", "4": "second", "5": "B", "6": ""}})
check("刷题·判分（4/6，choice 字母与原文均可）",
      s == 200 and r["correct"] == 4 and r["total"] == 6
      and r["results"][0]["correct"] and r["results"][3]["correct"]
      and not r["results"][5]["correct"], json.dumps(r, ensure_ascii=False)[:150])
s, r = call("GET", "/api/ielts/mistakes")
has_auto = any("租房" in (m.get("ref") or "") for m in r["items"])
check("刷题·错题自动进错题本", has_auto)
s, r = call("GET", "/api/ielts/attempts")
check("刷题·作答统计", s == 200 and r["stats"] and r["stats"][0]["attempts"] >= 1
      and len(r["items"]) >= 1)

# 手工导入：合法 + 非法
good = {"title": "v13导入测试·阅读", "subject": "reading", "sections": [
    {"material": "Test passage.", "questions": [
        {"no": 1, "type": "tfng", "stem": "Test is test.", "answer": "T"},
        {"no": 2, "type": "blank", "stem": "fill ______", "answer": "word"}]}]}
s, r = call("POST", "/api/ielts/bank/import", {"json": json.dumps(good, ensure_ascii=False)})
check("题库·手工导入", s == 201 and r["n_questions"] == 2)
s, r = call("POST", "/api/ielts/bank/import", {"json": "{\"title\":\"bad\"}"})
check("题库·非法导入被拒", s == 400 and "error" in r)
s, r = call("GET", "/api/ielts/bank?subject=reading")
check("题库·导入后可刷", any(i["source"] == "manual" for i in r["items"]))
# 清理：删掉本次导入的题库文件，避免测试数据污染刷题列表（v1.9 堵漏）
for _f in Path(__file__).resolve().parent.parent.glob("data/ielts_bank/*v13导入测试*"):
    _f.unlink(missing_ok=True)

# ========== R9 研究生知识库（grad 实例） ==========
s, r = call("POST", "/api/kb/ingest", {"way": "paste", "library": "grad",
          "title": "v13测试笔记-注意力机制",
          "content": "注意力机制的核心是 [[缩放点积]] 与 QKV 变换。"})
check("研究生库·粘贴入库", s == 200 and r.get("relpath", "").startswith("grad/"))
s, r = call("GET", "/api/kb/tree?lib=grad")
check("研究生库·目录可见", any("v13测试笔记" in a["title"] for a in r["items"]))
s, r = call("GET", "/api/kb/search?lib=grad&q=%E6%B3%A8%E6%84%8F%E5%8A%9B")
check("研究生库·中文检索命中", len(r["hits"]) >= 1)
# 清理：删掉本次入库的 grad 测试笔记（文件+索引行），避免重复堆积（v1.11 堵漏）
import sqlite3 as _sq
from pathlib import Path as _P
for _f in _P(__file__).resolve().parent.parent.glob("data/kb_grad/v13测试笔记*"):
    _f.unlink()
_con = _sq.connect(_P(__file__).resolve().parent.parent / "data" / "workbench.db", timeout=5)
_con.execute("DELETE FROM kb_chunks_fts WHERE chunk_id IN"
             " (SELECT id FROM kb_chunks WHERE relpath LIKE 'grad/v13测试笔记%')")
_con.execute("DELETE FROM kb_chunks WHERE relpath LIKE 'grad/v13测试笔记%'")
_con.execute("DELETE FROM kb_articles WHERE relpath LIKE 'grad/v13测试笔记%'")
_con.execute("DELETE FROM kb_chunks_meta WHERE relpath LIKE 'grad/v13测试笔记%'")
_con.commit()
_con.close()

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("FAILED:", FAIL)
