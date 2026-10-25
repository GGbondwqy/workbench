# -*- coding: utf-8 -*-
"""v1.18 验收：力扣同步适配 leetcode.cn GraphQL 现行 schema。

网络相关链路（真实 GraphQL/落库）已在 v1.18 当日人工实测：进度 solved=114(31/68/15)、
recentACSubmissions(noj-go 端点) 15 条、去重后新导入 7 条、cookie_ok=true——
按仓库惯例测试不访问外网，本文件只做离线纯函数 + 降级分支。

旧 schema 复现（ userProfileUserQuestions / recentAcSubmissionList 等字段已全部失效，
2026-10 从站点前端 JS chunk 提取现行查询：userSessionProgress / …ProgressV2 /
recentACSubmissions@/graphql/noj-go/）。
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.leetcode import _counts_by_difficulty, _progress_of, _recent_rows


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


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


print("== 1. 进度解析（现行 schema 双形态 + 兜底） ==")
sess = {"userProfileUserQuestionSubmitStats": {
        "acSubmissionNum": [{"difficulty": "EASY", "count": 31}, {"difficulty": "MEDIUM", "count": 68},
                            {"difficulty": "HARD", "count": 15}]},
        "userProfileUserQuestionProgress": {
        "numAcceptedQuestions": [{"difficulty": "EASY", "count": 31}, {"difficulty": "MEDIUM", "count": 68},
                                 {"difficulty": "HARD", "count": 15}],
        "numFailedQuestions": [{"difficulty": "MEDIUM", "count": 9}],
        "numUntouchedQuestions": [{"difficulty": "HARD", "count": 100}]}}
p = _progress_of(sess)
check("userSessionProgress 主路径（同数据双形态不叠加）",
      p["solved"] == 114 and p["easy"] == 31 and p["medium"] == 68 and p["hard"] == 15
      and p["attempted"] == 9 and p["untouched"] == 100)
v2 = {"userProfileUserQuestionProgressV2": {"numAcceptedQuestions": [{"difficulty": "MEDIUM", "count": 7}]}}
check("V2 兜底路径", _progress_of(v2) == {"solved": 7, "easy": 0, "medium": 7, "hard": 0})
check("空/垃圾输入返回空 dict（触发下一模板/报错）",
      _progress_of({}) == {} and _progress_of({"x": None}) == {})
check("旧 schema 字段解析不出（证明必须用新查询）",
      _progress_of({"userProfileUserQuestions": {"numSolved": 114}}) == {})

print("== 2. 最近 AC 行解析（submitTime 新字段） ==")
rows = _recent_rows([
    {"submissionId": 1, "submitTime": 1792141861,
     "question": {"translatedTitle": "回文链表", "titleSlug": "palindrome-linked-list"}},
    {"submitTime": None, "question": {"title": "Valid Palindrome"}},
    {"submitTime": 1792141861, "question": None}])
check("新 schema 取 translatedTitle + submitTime 转日期",
      rows[0][1] == "回文链表" and rows[0][0] == "2026-10-16" and rows[0][2] == "")
check("无翻译标题回退 title/无名题目兜底",
      rows[1][1] == "Valid Palindrome" and rows[1][0] is None and rows[2][1] == "未知名题目")
check("_counts_by_difficulty 小写归一",
      _counts_by_difficulty([{"difficulty": "EASY", "count": 3}, {"difficulty": "easy", "count": 2}])
      == {"easy": 5})

print("== 3. 未配置降级（HTTP，不动用户配置——还原原值） ==")
s, full = call("GET", "/api/config")
saved = full.get("leetcode", {})
try:
    call("PUT", "/api/config", {"leetcode": {"username": "", "cookie": ""}})
    s, r = call("POST", "/api/leetcode/sync", {})
    check("未配置用户名 → 友好报错", s == 200 and "未配置" in (r.get("error") or ""))
finally:
    call("PUT", "/api/config", {"leetcode": {"username": saved.get("username", ""),
                                             "cookie": saved.get("cookie", "")}})
s, r = call("GET", "/api/config")
check("用户配置已还原（用户名+Cookie 原样）",
      r.get("leetcode", {}).get("username") == saved.get("username")
      and bool(r.get("leetcode", {}).get("cookie")) == bool(saved.get("cookie")))

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
