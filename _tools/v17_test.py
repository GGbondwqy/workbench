# -*- coding: utf-8 -*-
"""v1.7 版本验收：项目式建课（文件夹浏览设施 + 一步创建）后端链路验证。"""
import json
import shutil
import tempfile
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


# ========== R1 文件夹浏览设施 ==========
s, r = call("GET", "/api/fs/folders")
check("fs·磁盘根列出盘符", s == 200 and r.get("path") == "" and len(r.get("folders", [])) >= 1,
      json.dumps(r, ensure_ascii=False)[:100])
# 回归：盘符行的 path 必须可直接打开（曾有 D::\ 双冒号 bug）
first_drive = r["folders"][0]["path"]
s, r = call("GET", f"/api/fs/folders?path={urllib.request.quote(first_drive)}")
check("fs·盘符行路径可直接进入", s == 200 and not r.get("error") and r.get("path") == first_drive,
      f"drive={first_drive} resp={json.dumps(r, ensure_ascii=False)[:80]}")
# 裸盘符归一："D:" 应按盘根处理而非盘上当前目录
if len(first_drive) == 3 and first_drive[1] == ":":
    s, r = call("GET", f"/api/fs/folders?path={urllib.request.quote(first_drive[:2])}")
    check("fs·裸盘符归一到盘根", s == 200 and not r.get("error") and r.get("path") == first_drive)

tmp = Path(tempfile.mkdtemp(prefix="v17fs_"))
(tmp / "第一章").mkdir()
(tmp / "第二章").mkdir()
(tmp / "notadir.txt").write_text("x", encoding="utf-8")
s, r = call("GET", f"/api/fs/folders?path={urllib.request.quote(str(tmp))}")
check("fs·子文件夹列出(仅目录)",
      s == 200 and sorted(f["name"] for f in r.get("folders", [])) == ["第一章", "第二章"]
      and r.get("parent"))

s, r = call("GET", "/api/fs/folders?path=" + urllib.request.quote(r["parent"]))
check("fs·父路径可导航", s == 200 and not r.get("error"))

s, r = call("GET", "/api/fs/folders?path=" + urllib.request.quote(r"D:\不存在的路径\v17"))
check("fs·错误路径返回可读错误", s == 200 and r.get("error"))

# ========== R2 项目式一步建课（文件夹+命名） ==========
course_tmp = Path(tempfile.mkdtemp(prefix="v17course_"))
(course_tmp / "第1讲.pptx").write_text("x", encoding="utf-8")
(course_tmp / "大纲.pdf").write_text("x", encoding="utf-8")

s, r = call("POST", "/api/grad/courses",
            {"name": "v17测试课-勿留", "folder_path": str(course_tmp)})
check("建课·文件夹随建课一步绑定", s == 201 and r.get("id"))
CID = r["id"]
s, r = call("GET", f"/api/grad/courses/{CID}")
check("建课·详情即含文件夹文件", s == 200 and r["course"]["folder_path"] == str(course_tmp)
      and len(r["files"]) == 2 and r["review_progress"]["total"] == 2)

s, r = call("POST", "/api/grad/courses", {"name": "v17裸课-勿留", "day_of_week": -1})
check("建课·无文件夹仍可建（纯网课）", s == 201)
BARE = r["id"]

s, r = call("POST", "/api/grad/courses",
            {"name": "v17坏夹-勿留", "folder_path": r"D:\不存在\x"})
check("建课·坏文件夹路径被拒", s == 400 and "error" in r)

# ========== R3 清理 ==========
s, r = call("GET", "/api/grad/courses")
for c in r["courses"]:
    if "v17" in c["name"]:
        call("DELETE", f"/api/grad/courses/{c['id']}")
s, r = call("GET", "/api/grad/courses")
check("建课·测试课程已清理", not any("v17" in c["name"] for c in r["courses"]))
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(course_tmp, ignore_errors=True)

print(f"\n===== v1.7 专项：{len(PASS)} 通过 / {len(FAIL)} 失败 =====")
if FAIL:
    for f in FAIL:
        print("  FAIL:", f)
    raise SystemExit(1)
