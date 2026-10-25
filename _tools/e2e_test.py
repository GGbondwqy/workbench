# -*- coding: utf-8 -*-
"""端到端功能验收：模拟真实用户一天的完整操作（覆盖全部 8 个页面的后端链路）。"""
import atexit
import json
import urllib.request
from datetime import date

B = "http://127.0.0.1:8787"
TODAY = date.today().isoformat()
PASS, FAIL = [], []

# e2e 全程临时停用 AI（回归只验业务链路，AI 真实性由 v20 的 mock 覆盖）——
# 避免 AI 启用时用例打真实计费 API 且受中转站快慢影响（v1.11 实测 60s 超时）。
# atexit 保证任何退出路径都恢复用户的启用状态。
_ai_prev = None


def _cfg_put(body):
    req = urllib.request.Request(B + "/api/config", data=json.dumps(body).encode(),
                                 method="PUT", headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=90).read()


def _ai_off():
    global _ai_prev
    with urllib.request.urlopen(B + "/api/config", timeout=90) as r:
        _ai_prev = json.loads(r.read())["ai"]["active"]
    _cfg_put({"ai": {"active": None}})


def _ai_restore():
    if _ai_prev is not None:
        try:
            _cfg_put({"ai": {"active": _ai_prev}})
        except Exception:
            pass


atexit.register(_ai_restore)
_ai_off()


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


# ========== 工作台 ==========
s, r = call("POST", "/api/plan/confirm", {"date": TODAY, "items": [
    {"title": "精读 TCP 拥塞控制", "est": 40}, {"title": "刷 2 道链表题", "est": 30}]})
check("规划确认→生成任务（v1.3 起不再生成学习块）", s == 200 and len(r["tasks"]) == 2 and "blocks" not in r,
      json.dumps(r, ensure_ascii=False)[:120])

s, r = call("POST", "/api/tasks", {"title": "手动任务", "plan_date": TODAY, "priority": "high"})
tid = r.get("id")
check("新建任务", s == 201 and tid is not None)

s, r = call("POST", f"/api/tasks/{tid}/complete")
check("完成任务", r.get("status") == "done")

s, r = call("GET", "/api/dashboard")
check("首页聚合(任务/无复盘字段/v1.6无建议)",
      r["task_stats"]["total"] >= 3 and "suggestions" not in r
      and "habits" not in r and "journal" not in r and "timeline" not in r)

# ========== 复盘（v1.3 页面层移除；journal/habit 服务保留，接口仍可用） ==========
s, r = call("PUT", f"/api/journal/{TODAY}", {"content": "工作台全功能验收日"})
check("一句话日志（服务保留）", r.get("content") == "工作台全功能验收日")

s, r = call("GET", "/api/habits")
hid = r["habits"][0]["id"]
call("POST", f"/api/habits/{hid}/checkin")
s, r = call("GET", "/api/habits")
check("习惯打卡（服务保留）", r["habits"][0]["checked_today"] and r["habits"][0]["streak"] >= 1)

# ========== 目标 ==========
s, r = call("GET", "/api/goals")
goal = next((g for g in r["goals"] if "实习" in g["title"]), None)
check("目标列表+进度", goal is not None and goal["progress"] >= 0)

gid = goal["id"]
s, r = call("PUT", f"/api/goals/{gid}/deadline", {"deadline": "2027-06-01"})
check("设置截止日", s == 200)

# ========== 英语 ==========
s, r = call("GET", "/api/vocab/queue")
check("复习队列", len(r["queue"]) >= 1)
wid = r["queue"][0]["id"]
s, r = call("POST", f"/api/vocab/review/{wid}", {"grade": 3})
check("SRS评分→间隔更新", r.get("interval", 0) >= 3, str(r))

s, r = call("POST", "/api/vocab/words/import", {"text": "resilient 有弹性的\nempirical 实证的"})
# 幂等：重复跑 e2e 时词已在库，imported=0 属正常（词已可复习）
check("生词导入", r.get("imported") in (0, 2), str(r))

s, r = call("POST", "/api/vocab/practices", {"kind": "listening", "minutes": 25, "note": "剑桥真题S1"})
check("精听打卡", s == 201)

# 复习完成事件 → 背单词自动点亮（先取消手动打的，验证事件路径）
call("POST", f"/api/habits/{hid}/checkin", {"undo": True})
s, r = call("POST", "/api/vocab/finish", {"count": 5})
s, r = call("GET", "/api/habits")
h = r["habits"][0]
check("事件联动:复习完成→自动点亮背单词", h["checked_today"] is True,
      str(r["habits"][:1]))

# ========== 研究生 ==========
s, r = call("POST", "/api/grad/courses", {"name": "高等机器学习", "day_of_week": date.today().weekday(),
                                          "start_time": "14:00", "end_time": "16:00", "place": "A-301"})
check("添加课程", s == 201)
_course_id = r.get("id")
s, r = call("GET", "/api/schedule/today")
check("课程→时间轴固定块联动", any("机器学习" in b["title"] for b in r["blocks"]), str(r["blocks"])[:150])
call("DELETE", f"/api/grad/courses/{_course_id}")  # v1.7 起随手清理，不再每次漏一门重复课

s, r = call("POST", "/api/grad/meetings", {"meet_date": TODAY, "notes": "汇报工作台进度"})
check("组会记录", s == 201)
_mid = r.get("id")
call("DELETE", f"/api/grad/meetings/{_mid}")  # v1.8 起随手清理

s, r = call("POST", "/api/grad/advisor", {"content": "跑一组消融实验"})
aid = r["id"]
s, r = call("POST", f"/api/grad/advisor/{aid}/convert")
check("导师任务→今日待办(高优)", r.get("source") == "advisor" and r.get("priority") == "high", str(r)[:150])
call("DELETE", f"/api/grad/advisor/{aid}")  # v1.8 起随手清理

bbt = [{"id": "ABC123", "title": "Attention Is All You Need", "creators": [{"name": "Vaswani A."}],
        "issued": {"date-parts": [[2017]]}, "type": "paper-conference"},
       {"id": "DEF456", "title": "BERT", "creators": [{"name": "Devlin J."}],
        "issued": {"date-parts": [[2019]]}}]
s, r = call("POST", "/api/papers/import", {"text": json.dumps(bbt, ensure_ascii=False)})
# 幂等：重复跑 e2e 时文献已在库（added=0+merged），下方"重复导入"项验证合并路径
check("Zotero BBT 导入(去重合并)", r.get("added") in (0, 2) and (r.get("merged") or 0) >= 0)
s, r = call("POST", "/api/papers/import", {"text": json.dumps(bbt[:1], ensure_ascii=False)})
check("重复导入→合并不重复", r.get("added") == 0 and r.get("merged") == 1, str(r))
s, r = call("GET", "/api/papers")
pid = r["papers"][0]["id"]
s, r = call("PUT", f"/api/papers/{pid}/status", {"status": "reading"})
check("文献状态流转", s == 200)

# ========== 就业 ==========
s, r = call("GET", "/api/career/kb-plan?daily=2")
check("八股计划(328篇拆每日)", r.get("available") and r["total"] == 328
      and r["remaining"] >= 200 and len(r["items"]) == 2,  # remaining 单调递减，写死 300 对真实使用必挂（v1.11）
      str(r)[:150])
_e2e_read_paths = []
if r.get("items"):
    _e2e_read_paths.append(r["items"][0]["relpath"])
    s, r2 = call("POST", "/api/career/kb-read", {"relpath": r["items"][0]["relpath"]})
    check("八股阅读打卡", r2.get("ok") is True)
    s, r2 = call("GET", "/api/career/kb-plan?daily=2")
    check("阅读后剩余-1", r2["remaining"] == r["remaining"] - 1 if "remaining" in r2 else False, str(r2)[:100])

s, r = call("POST", "/api/career/problems", {"title": "LRU 缓存", "topic": "哈希", "difficulty": "中等"})
check("刷题打卡", s == 201)
_problem_id = r.get("id")
s, r = call("GET", "/api/career/problems")
check("刷题统计+里程碑联动", r["stats"]["total"] >= 1)
# 刷题打卡无删除端点：末尾 sqlite 回滚（v1.18 起不再每次积累一条重复打卡）

s, r = call("POST", "/api/career/applications", {"company": "字节跳动", "position": "后端日常实习", "channel": "牛客"})
app_id = r.get("id")
check("新增投递", app_id is not None)
for st in ["written", "interview1"]:
    s, r = call("POST", f"/api/career/applications/{app_id}/advance", {"status": st})
check("投递状态推进+轨迹留痕", r.get("status") == "interview1" and len(r.get("timeline", [])) == 3, str(r)[:200])
call("DELETE", f"/api/career/applications/{app_id}")   # v1.19 起随手清理（曾有 45 条"一面"面板积累）

# ========== 资料库 ==========
s, r = call("GET", "/api/kb/search?q=" + urllib.request.quote("三次握手"))
check("中文全文检索", len(r.get("hits", [])) >= 3, str(r)[:120])

rel = r["hits"][0]["relpath"]
s, r = call("GET", "/api/kb/article?path=" + urllib.request.quote(rel))
check("文章阅读(库外正文)", len(r.get("body", "")) > 500)

_, boot = call("GET", "/api/bootstrap")
ai_on = bool(boot["ai"]["configured"])
_, r = call("POST", "/api/kb/ask", {"q": "什么是时间复杂度"})
check(f"问答(AI{'直答' if ai_on else '未配置→降级命中列表'})",
      r.get("ai_used") is ai_on and len(r.get("sources", [])) >= 1)

s, r = call("POST", "/api/kb/clips", {"title": "字节面经-Go方向", "link": "https://example.com"})
check("面经收藏", s == 201 and r.get("id"))
_clip_id = r.get("id")   # v1.20 自清洁：收藏随手删，不再污染快速收藏列表

# ========== 目标进度最终联动 ==========
s, r = call("GET", "/api/goals")
intern = next(g for g in r["goals"] if "实习" in g["title"])
check("里程碑进度被任务/八股/刷题推进", intern["progress"] > 0, f"progress={intern['progress']}")

# ========== 配置热更新 ==========
s, r = call("GET", "/api/config")
_prev_active = r["ai"]["active"]   # 保护用户真实启用的档案
s, r = call("PUT", "/api/config", {"ai": {"providers": [
    {"name": "test-relay", "base_url": "https://x.example.com/v1", "model": "m1", "api_key": "sk-test"}]}})
check("AI档案保存+热生效", any(p.get("name") == "test-relay"
                               for p in r.get("ai", {}).get("providers", [])))
s, r = call("PUT", "/api/config", {"ai": {"active": "test-relay"}})
check("切换启用档案", r.get("ai", {}).get("configured") is True)
if _prev_active and _prev_active != "test-relay":
    call("PUT", "/api/config", {"ai": {"active": _prev_active}})   # 恢复用户配置
else:
    call("PUT", "/api/config", {"ai": {"active": None}})  # 原本就是降级态则恢复降级
s, r = call("GET", "/api/config")
check("配置读取不泄露密钥", all("api_key" not in p and "sk-test" not in json.dumps(p)
                                for p in r["ai"]["providers"]))
# 自清洁：删掉本用例创建的 test-relay 档案（v1.13 起支持删除；此前每次跑测都残留一个）
call("PUT", "/api/config", {"ai": {"remove_provider": "test-relay"}})

# ========== 自清洁（v1.8：测试数据随手删，不再污染用户工作台） ==========
_s, _d = call("GET", "/api/dashboard")
for _t in _d["tasks"]:
    if _t["title"] in ("手动任务", "手动任务（已改名 v1.3）", "精读 TCP 拥塞控制", "刷 2 道链表题") \
       or (_t["title"] == "跑一组消融实验" and _t.get("source") == "advisor"):
        call("DELETE", f"/api/tasks/{_t['id']}")

# 八股阅读打卡是用户真实数据域：回滚本次 e2e 读的篇目，否则 remaining 日渐缩水
# （v1.11 实测：多次跑测后 remaining 294 < 300 断言挂）
import sqlite3 as _sq
from pathlib import Path as _P
_con = _sq.connect(_P(__file__).resolve().parent.parent / "data" / "workbench.db", timeout=5)
for _rel in _e2e_read_paths:
    _con.execute("DELETE FROM career_kb_reads WHERE date=? AND relpath=?", (TODAY, _rel))
if globals().get("_problem_id"):
    _con.execute("DELETE FROM career_problems WHERE id=?", (_problem_id,))  # v1.18 自清洁
_con.commit()
_con.close()
if globals().get("_clip_id"):
    # v1.20 自清洁：面经收藏走 API（须在本地 sqlite 写事务结束后，否则服务端写库被锁 500）
    call("DELETE", f"/api/kb/clips/{_clip_id}")
print(f"\n===== 通过 {len(PASS)} / 失败 {len(FAIL)} =====")
if FAIL:
    print("失败项：", FAIL)
