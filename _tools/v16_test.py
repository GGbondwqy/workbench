# -*- coding: utf-8 -*-
"""v1.6 版本验收：工作台去建议 + 课程详情化（文件/复习/作业）后端链路验证。

说明：open 接口会真的调系统默认程序打开文件（用户桌面弹窗），测试只验校验失败
分支（外来路径 400），不做真实打开——真实打开由人工验收。
"""
import json
import shutil
import tempfile
import urllib.request
from datetime import date, timedelta
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


TODAY = date.today()
D_OVERDUE = (TODAY - timedelta(days=1)).isoformat()
D_SOON = (TODAY + timedelta(days=2)).isoformat()

# ========== R1 工作台：三件事建议已移除 ==========
s, r = call("GET", "/api/dashboard")
check("工作台·聚合无建议字段(v1.6)", s == 200 and "suggestions" not in r and "tasks" in r)

# ========== R2 课程自建：时间选填 + 日程块联动 ==========
s, r = call("POST", "/api/grad/courses", {"name": "v16测试课A-勿留", "day_of_week": -1})
check("课程·无固定时间可建", s == 201 and r.get("id"))
A = r["id"]

some_wed = (TODAY + timedelta(days=(2 - TODAY.weekday()) % 7 or 7)).isoformat()  # 下个周三
s, r = call("POST", "/api/grad/courses",
            {"name": "v16测试课B-勿留", "day_of_week": 2,
             "start_time": "10:00", "end_time": "11:40", "place": "A栋101"})
check("课程·固定时间可建", s == 201 and r.get("id"))
BID = r["id"]

s, r = call("GET", "/api/grad/courses")
ca = next((c for c in r["courses"] if c["id"] == A), None)
cb = next((c for c in r["courses"] if c["id"] == BID), None)
check("课程·列表含计划信息", ca and not ca["has_schedule"] and ca["open_assignments"] == 0
      and cb and cb["has_schedule"] and cb["file_count"] == 0)

s, r = call("GET", f"/api/schedule/today?date={some_wed}")
check("课程·固定块进入日程联动", s == 200
      and any(b["title"] == "v16测试课B-勿留" for b in r["blocks"]))

s, r = call("PUT", f"/api/grad/courses/{BID}", {"day_of_week": -1})
s, r = call("GET", f"/api/schedule/today?date={some_wed}")
check("课程·改为无固定时间后块移除", s == 200
      and not any(b["title"] == "v16测试课B-勿留" for b in r["blocks"]))

# ========== R3 文件夹绑定 + 文件列表 + 复习标记 ==========
tmp = Path(tempfile.mkdtemp(prefix="v16kb_"))
(tmp / "第1讲.pptx").write_text("x", encoding="utf-8")
(tmp / "讲义.pdf").write_text("x", encoding="utf-8")
(tmp / "~$第1讲.pptx").write_text("x", encoding="utf-8")      # Office 临时文件应过滤
(tmp / ".hidden.txt").write_text("x", encoding="utf-8")        # 隐藏文件应过滤
(tmp / "子目录").mkdir()
FOLDER = str(tmp)

s, r = call("PUT", f"/api/grad/courses/{A}", {"folder_path": FOLDER})
check("文件夹·绑定成功", s == 200 and r.get("folder_path") == FOLDER)

s, r = call("PUT", f"/api/grad/courses/{A}", {"folder_path": r"D:\不存在\v16"})
check("文件夹·不存在被拒", s == 400 and "error" in r)

s, r = call("GET", f"/api/grad/courses/{A}")
names = [f["name"] for f in r["files"]]
check("文件列表·只列真实文件(滤临时/隐藏/子目录)",
      names == ["第1讲.pptx", "讲义.pdf"] and r["review_progress"] == {"reviewed": 0, "total": 2})

ppt_path = str(tmp / "第1讲.pptx")
s, r = call("POST", f"/api/grad/courses/{A}/review", {"path": ppt_path, "reviewed": True})
s, r = call("GET", f"/api/grad/courses/{A}")
f0 = next(f for f in r["files"] if f["name"] == "第1讲.pptx")
check("复习·标记记当日+进度", s == 200 and f0["reviewed"]
      and f0["reviewed_date"] == TODAY.isoformat()
      and r["review_progress"]["reviewed"] == 1)

s, r = call("POST", f"/api/grad/courses/{A}/review", {"path": ppt_path, "reviewed": False})
s, r = call("GET", f"/api/grad/courses/{A}")
check("复习·取消回退进度", r["review_progress"]["reviewed"] == 0)

# ========== R4 零散文件 ==========
loose_dir = Path(tempfile.mkdtemp(prefix="v16loose_"))
loose_file = loose_dir / "散落笔记.docx"
loose_file.write_text("x", encoding="utf-8")

s, r = call("POST", f"/api/grad/courses/{A}/files", {"path": str(loose_file)})
check("零散·登记成功", s == 201 and r.get("id"))
loose_id = r["id"]

s, r = call("GET", f"/api/grad/courses/{A}")
lf = next((f for f in r["files"] if f.get("loose")), None)
check("零散·进列表带标记+计进度", lf and lf["name"] == "散落笔记.docx"
      and r["review_progress"]["total"] == 3)

s, r = call("POST", f"/api/grad/courses/{A}/files", {"path": r"D:\不存在\x.docx"})
check("零散·不存在被拒", s == 400)

s, r = call("DELETE", f"/api/grad/courses/{A}/files/{loose_id}")
s, r = call("GET", f"/api/grad/courses/{A}")
check("零散·移除登记", not any(f.get("loose") for f in r["files"])
      and r["review_progress"]["total"] == 2)

# ========== R5 打开校验（不真实打开，避免弹窗） ==========
outside = loose_dir / "外来文件.txt"
outside.write_text("x", encoding="utf-8")
s, r = call("POST", f"/api/grad/courses/{A}/open", {"path": str(outside)})
check("打开·外来路径被拒", s == 400 and "error" in r)
s, r = call("POST", f"/api/grad/courses/{A}/review", {"path": str(outside), "reviewed": True})
check("复习·外来路径同样被拒", s == 400)

# ========== R6 作业 ==========
s, r = call("POST", f"/api/grad/courses/{A}/assignments",
            {"title": "过期作业", "due_date": D_OVERDUE})
check("作业·过期可建", s == 201)
a_over = r["id"]
s, r = call("POST", f"/api/grad/courses/{A}/assignments",
            {"title": "临期作业", "due_date": D_SOON, "note": "实验报告",
             "file_ref": ppt_path})
a_soon = r["id"]
s, r = call("POST", f"/api/grad/courses/{A}/assignments", {"title": "无截止作业"})
a_none = r["id"]
check("作业·无截止可建", s == 201)

s, r = call("GET", f"/api/grad/courses/{A}")
amap = {a["title"]: a for a in r["assignments"]}
check("作业·days_left 计算(过期-1/临期2/无截止None)",
      amap["过期作业"]["days_left"] == -1 and amap["临期作业"]["days_left"] == 2
      and amap["无截止作业"]["days_left"] is None)
check("作业·按截止日升序排列",
      [a["title"] for a in r["assignments"]] == ["过期作业", "临期作业", "无截止作业"]
      and r["open_assignments"] == 3)

s, r = call("POST", f"/api/grad/assignments/{a_over}/convert")
check("作业·过期转待办=高优先级", s == 200 and r.get("source") == "course"
      and r.get("priority") == "high" and "课程作业" in r.get("title", ""))
tid = r.get("id")

s, r = call("GET", "/api/dashboard")
check("作业·转待办进入今日清单", any(t["id"] == tid for t in r["tasks"]))

s, r = call("POST", f"/api/grad/assignments/{a_over}/convert")
check("作业·重复转被拒", s == 400)

s, r = call("PUT", f"/api/grad/assignments/{a_soon}", {"status": "done"})
s, r = call("GET", f"/api/grad/courses/{A}")
check("作业·勾完成+开放数减少",
      next(a for a in r["assignments"] if a["id"] == a_soon)["status"] == "done"
      and r["open_assignments"] == 2)

s, r = call("PUT", f"/api/grad/assignments/{a_none}", {"status": "weird"})
check("作业·非法状态被拒", s == 400)

s, r = call("POST", f"/api/grad/courses/{A}/assignments", {"title": ""})
check("作业·空标题被拒", s == 400)

s, r = call("DELETE", f"/api/grad/assignments/{a_none}")
s, r = call("GET", f"/api/grad/courses/{A}")
check("作业·删除", not any(a["id"] == a_none for a in r["assignments"]))

# ========== R7 课程删除连带清理 ==========
s, r = call("DELETE", f"/api/grad/courses/{A}")
s, r = call("GET", f"/api/grad/courses/{A}")
check("课程·删除后详情404", s == 404)
s, r = call("DELETE", f"/api/grad/courses/{BID}")
s, r = call("GET", "/api/grad/courses")
check("课程·测试课程已清干净",
      not any("v16测试" in c["name"] for c in r["courses"]))
if tid:
    call("DELETE", f"/api/tasks/{tid}")  # 清理转出的测试任务

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(loose_dir, ignore_errors=True)

print(f"\n===== v1.6 专项：{len(PASS)} 通过 / {len(FAIL)} 失败 =====")
if FAIL:
    for f in FAIL:
        print("  FAIL:", f)
    raise SystemExit(1)
