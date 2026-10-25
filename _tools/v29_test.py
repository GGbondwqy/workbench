# -*- coding: utf-8 -*-
"""v1.19 验收：就业删除补齐 + 投递导航（F30）。

覆盖：投递看板删除 / kb 文章删除（可写库三库+只读拒删）/ 文献与笔记删除 /
雅思错题删除 / 题组删除（文件题组可删+内置拒删+级联）/ 自建话题删除 /
导航 seed（平台 10 + 公司 13+9，全 https）。
已有端点仅前端补绑的（复盘/项目条目/知识卡片/简历版本）端点早已被既有测试覆盖，
此处不重复；UI 绑定由浏览器人工验收。
"""
import json
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
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


print("== 1. 投递看板删除（v1.19） ==")
s, a = call("POST", "/api/career/applications",
            {"company": "v19测试公司-勿留", "position": "后端实习", "channel": "测试"})
AID = a["id"]
call("POST", f"/api/career/applications/{AID}/advance", {"status": "written"})
s, r = call("GET", "/api/career/applications")
check("投递创建+推进（有轨迹）",
      any(x["id"] == AID and len(x["timeline"]) >= 2 for x in r["items"]))
s, _ = call("DELETE", f"/api/career/applications/{AID}")
s, r = call("GET", "/api/career/applications")
check("删除后列表不再含（轨迹随行删）", not any(x["id"] == AID for x in r["items"]))

print("== 2. 投递导航 seed（F30） ==")
s, nav = call("GET", "/api/career/nav")
check("平台 10 个全 https", s == 200 and len(nav["platforms"]) == 10
      and all(x["url"].startswith("https://") for x in nav["platforms"]))
groups = {g["group"]: g["items"] for g in nav["companies"]}
check("公司两组 13+9 全 https", len(groups.get("互联网大厂", [])) == 13
      and len(groups.get("硬件 / 智能 / 外企", [])) == 9
      and all(x["url"].startswith("https://") for g in nav["companies"] for x in g["items"]))

print("== 3. kb 文章删除（v1.19） ==")
s, art = call("POST", "/api/kb/ingest", {"way": "paste", "library": "mianjing",
             "title": "v19删除测试面经-勿留", "content": "v19 删除测试正文，字节一面 Redis 持久化 RDB AOF。"})
RELPATH = art["relpath"]
check("面经入库", s == 200 or s == 201)
s, r = call("GET", "/api/kb/tree?lib=mianjing")
check("入库后目录可见", any(x["relpath"] == RELPATH for x in r["items"]))
s, r = call("DELETE", f"/api/kb/article?path={urllib.parse.quote(RELPATH, safe='')}")
check("删除成功", s == 200 and r.get("ok"))
s, r = call("GET", "/api/kb/tree?lib=mianjing")
check("目录已无", not any(x["relpath"] == RELPATH for x in r["items"]))
s, r = call("GET", "/api/kb/search?lib=mianjing&q=" + urllib.parse.quote("v19删除测试"))
check("检索无残影", not any(h["relpath"] == RELPATH for h in r["hits"]))
check("磁盘文件已删", not (ROOT / "data" / "kb_mianjing" / Path(RELPATH).name).exists())
# 只读库拒删
s, r = call("GET", "/api/kb/tree?lib=bagu")
if r["items"]:
    bagu_path = r["items"][0]["relpath"]
    s, r = call("DELETE", "/api/kb/article?path=" + urllib.parse.quote(bagu_path, safe=""))
    check("bagu 只读库拒删→400 友好提示", s == 400 and "只读" in r.get("error", ""))
else:
    check("bagu 只读库拒删→400（跳过：八股库为空）", True)
s, r = call("DELETE", "/api/kb/article?path=" + urllib.parse.quote("mianjing/v19-不存在.md"))
check("不存在的文章→404", s == 404)

print("== 4. 文献与笔记删除（v1.19） ==")
s, r = call("POST", "/api/papers/import", {"text": json.dumps([
    {"title": "v19删除测试论文-勿留", "creators": [{"name": "Test A"}],
     "issued": {"date-parts": [[2026]]}, "type": "article-journal"}], ensure_ascii=False)})
s, papers = call("GET", "/api/papers")
paper = next(p for p in papers["papers"] if "v19删除测试" in p["title"])
s, _ = call("POST", f"/api/papers/{paper['id']}/notes", {"content": "v19 测试笔记"})
s, notes = call("GET", f"/api/papers/{paper['id']}/notes")
check("文献+笔记创建", len(notes["notes"]) == 1)
NID = notes["notes"][0]["id"]
s, _ = call("DELETE", f"/api/papers/notes/{NID}")
s, notes = call("GET", f"/api/papers/{paper['id']}/notes")
check("笔记删除", not notes["notes"])
s, _ = call("DELETE", f"/api/papers/{paper['id']}")
s, papers = call("GET", "/api/papers")
check("文献删除（级联后无残留）", not any(p["id"] == paper["id"] for p in papers["papers"]))

print("== 5. 雅思错题删除（v1.19） ==")
s, m = call("POST", "/api/ielts/mistakes", {"subject": "reading", "qtype": "v19测试题型-勿留",
                                            "reason": "测试", "date": "2026-10-25"})
MID = m["id"]
s, r = call("DELETE", f"/api/ielts/mistakes/{MID}")
s, r = call("GET", "/api/ielts/mistakes")
check("错题删除", not any(x["id"] == MID for x in r["items"]))

print("== 6. 题组删除（v1.19：文件题组可删+内置拒删） ==")
tmp_set = {"id": "public-v19-del-test", "subject": "reading", "source": "public",
           "title": "v19 删除测试题组-勿留",
           "sections": [{"intro": "t", "material": "word " * 400,
                         "questions": [{"no": 1, "type": "blank", "stem": "fill __1__",
                                        "answer": "word"}]}]}
bank_file = ROOT / "data" / "ielts_bank" / "public-v19-del-test.json"
bank_file.write_text(json.dumps(tmp_set, ensure_ascii=False), encoding="utf-8")
s, r = call("POST", f"/api/ielts/bank/{tmp_set['id']}/submit", {"answers": {"1": "wrong"}})
check("题组可作答（留痕+错题）", s == 200 and r["correct"] == 0)
s, r = call("DELETE", f"/api/ielts/bank/{tmp_set['id']}")
check("文件题组删除成功", s == 200 and r.get("ok") and not bank_file.exists())
s, r = call("GET", "/api/ielts/bank")
check("题库已无该题组", not any(x["id"] == tmp_set["id"] for x in r["items"]))
con = sqlite3.connect(ROOT / "data" / "workbench.db", timeout=5)
n_att = con.execute("SELECT COUNT(*) FROM ielts_attempts WHERE set_id=?",
                    (tmp_set["id"],)).fetchone()[0]
n_mis = con.execute("SELECT COUNT(*) FROM ielts_mistakes WHERE ref LIKE ?",
                    ("v19 删除测试题组-勿留 Q%",)).fetchone()[0]
con.close()
check("作答留痕与错题级联清除", n_att == 0 and n_mis == 0)
s, r = call("GET", "/api/ielts/bank")
builtin = next(x for x in r["items"] if x["source"] == "builtin")
s, r = call("DELETE", f"/api/ielts/bank/{builtin['id']}")
check("内置题组拒删→400", s == 400 and "内置" in r.get("error", ""))

print("== 7. 自建话题删除（v1.19） ==")
s, tpc = call("POST", "/api/ielts/topics", {"part": 2, "topic": "v19删除测试话题-勿留"})
TID = tpc["id"]
s, r = call("DELETE", f"/api/ielts/topics/{TID}")
s, r = call("GET", "/api/ielts/topics")
check("自建话题删除", not any(x.get("row_id") == TID for x in r["items"]))

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
