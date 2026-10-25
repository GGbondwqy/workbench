# -*- coding: utf-8 -*-
"""v1.11 验收：资料库分库——检索/提问按 library 过滤；测试数据自清洁。

提问走降级路径（临时停用 AI）避免真实计费；grad 测试文章用 sqlite+文件双清。
"""
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


Q = "v21分库测试·缩放点积注意力"
print("== 1. 入库一篇 grad 测试文章 ==")
s, r = call("POST", "/api/kb/ingest", {"way": "paste", "library": "grad",
          "title": "v21分库测试笔记", "content": "缩放点积注意力是 Transformer 的核心：QKV 相似度按维度开根缩放。"})
check("grad 入库成功", s == 200 and r.get("relpath", "").startswith("grad/"))
relpath = r.get("relpath", "")

print("== 2. 检索分库 ==")
s, r = call("GET", f"/api/kb/search?lib=grad&q={urllib.request.quote(Q[:10])}")
check("grad 库内命中", s == 200 and r["hits"]
      and all(h["library"] == "grad" for h in r["hits"]))
s, r = call("GET", f"/api/kb/search?lib=bagu&q={urllib.request.quote(Q[:10])}")
check("bagu 库内无该文", s == 200 and all("v21分库测试" not in h["title"] for h in r["hits"])
      and all(h["library"] == "bagu" for h in r["hits"]))
s, r = call("GET", f"/api/kb/search?q={urllib.request.quote(Q[:10])}")
check("全部=跨库混合（含 grad 命中）", s == 200
      and any(h["library"] == "grad" and "v21分库测试" in h["title"] for h in r["hits"]))

print("== 3. 提问分库（临时停用 AI 走降级，避免计费） ==")
s, cfg = call("GET", "/api/config")
prev_active = cfg["ai"]["active"]
try:
    call("PUT", "/api/config", {"ai": {"active": None}})
    s, r = call("POST", "/api/kb/ask", {"q": Q, "library": "grad"})
    check("grad 提问·AI 降级", s == 200 and r["ai_used"] is False)
    check("grad 提问·来源全在 grad", r["sources"]
          and all(x["relpath"].startswith("grad/") for x in r["sources"]))
    s, r = call("POST", "/api/kb/ask", {"q": Q, "library": "mianjing"})
    check("mianjing 提问·无料可答", s == 200
          and not any("v21分库测试" in x["relpath"] for x in r["sources"]))
finally:
    call("PUT", "/api/config", {"ai": {"active": prev_active}})
s, cfg = call("GET", "/api/config")
check("AI 启用状态已恢复", cfg["ai"]["active"] == prev_active)

print("== 4. 自清洁：删 grad 测试文章（文件+全部索引行） ==")
# ingest 遇同名文件会加 -1/-2 后缀（kb.ingest 的 while path.exists()），
# 所以文件与 db 行都按 LIKE 通配清，不能只删 ingest 返回的那一个 relpath
for _f in ROOT.glob("data/kb_grad/v21分库测试笔记*.md"):
    _f.unlink()
con = sqlite3.connect(ROOT / "data" / "workbench.db", timeout=5)
# 注意：kb_chunks_meta（分块指纹）必须一起删——否则同标题同内容重入时
# digest 命中旧指纹被跳过，chunks 是空的（v1.11 实测踩坑）；kb_fts 文章级索引也要删
for _sql in (
    "DELETE FROM kb_chunks_fts WHERE chunk_id IN"
    " (SELECT id FROM kb_chunks WHERE relpath LIKE 'grad/v21分库测试笔记%')",
    "DELETE FROM kb_chunks WHERE relpath LIKE 'grad/v21分库测试笔记%'",
    "DELETE FROM kb_articles WHERE relpath LIKE 'grad/v21分库测试笔记%'",
    "DELETE FROM kb_chunks_meta WHERE relpath LIKE 'grad/v21分库测试笔记%'",
    "DELETE FROM kb_fts WHERE relpath LIKE 'grad/v21分库测试笔记%'",
):
    _n = con.execute(_sql).rowcount
    print(f"    [cleanup {_n} rows] {_sql[:44]}")
con.commit()
con.close()
s, r = call("GET", f"/api/kb/search?q={urllib.request.quote(Q[:10])}")
check("测试文章已清", not any("v21分库测试" in h["title"] for h in r["hits"]))

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
