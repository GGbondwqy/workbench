# -*- coding: utf-8 -*-
"""v1.20 验收：面经收藏删除（补自清洁）+ 力扣独立页（本地文件夹/问 AI F31/到期复习 F32）。

自建本地 mock OpenAI（判分/问答分流，沿用 v20/v27 手法，不覆盖用户密钥、测完恢复）；
力扣文件夹用系统临时目录（lj.py init+add 搭真学习体系），测完连同磁盘目录一并清理；
复习打卡回写在临时夹具上验证，绝不触碰用户真实复习清单。纯函数离线单测不访问外网。
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []
ROOT = Path(__file__).resolve().parent.parent
REAL_FOLDER = str(ROOT.parent / "leetcode")   # 用户真实力扣文件夹（测完恢复绑定）


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}


def check(name, ok, extra=""):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name + (f"  [{extra}]" if extra and not ok else ""))


# ---------- mock OpenAI（按 system 提示分流） ----------
class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(n) or b"{}")
        if self.path.endswith("/chat/completions"):
            msgs = payload.get("messages") or []
            sys_msg = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
            user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
            if "面试官" in sys_msg:                    # F32 判分
                content = "过\n要点命中，思路正确。"
            elif "mock-ask-坏例" in user:              # 问答一般路径仍可答
                content = "这不是我要的"
            else:                                      # F31 问答
                content = "【mock】依据学习笔记：滑动窗口左边界单调前进，保证每个字符至多进出各一次。"
            return self._json({
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70}})
        return self._json({"error": "not found"}, 404)


srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
MOCK = f"http://127.0.0.1:{srv.server_address[1]}/v1"
threading.Thread(target=srv.serve_forever, daemon=True).start()

# ---------- 纯函数离线单测（不访问外网/服务） ----------
sys.path.insert(0, str(ROOT))
from app.services import leetcode as L  # noqa: E402

print("== 0. 纯函数（离线） ==")
note = "# 学习笔记\n\n## 双指针\n\n### K-1 [知识点] 甲\n- **问**：q1 第一行\nq1 第二行\n- **答**：a1\n\n### K-2 [Bug] 乙|丙\n- **问**：q2\n- **答**：a2\n\n## 待归档区\n\n### K-3 [设计] 丙\n- **问**：q3\n"
cards = L._cards_of(note)
check("_cards_of 解析三卡", set(cards) == {"K-1", "K-2", "K-3"})
check("_cards_of 章节归属", cards["K-1"]["chapter"] == "双指针" and cards["K-3"]["chapter"] == "待归档区")
check("_field_of 跨行取值", cards["K-1"]["body"].count("q1") == 2 and L._field_of(cards["K-1"]["body"], "问").startswith("q1"))
check("_due_count 跳过表头与✅", L._due_count(
    "| ID | 章节 | 标题 | 状态 | 下次复习 | 阶段 | 锚点 |\n| --- | --- | --- | --- | --- | --- | --- |\n"
    "| K-1 | 双指针 | a | ✅ | 2020-01-01 | 1 | x |\n"
    "| K-2 | 双指针 | b | ⬜ | 2020-01-01 | 0 | x |\n"
    "| K-3 | 双指针 | c | 📌 | 2099-01-01 | 2 | x |\n") == 1)
rows = L._parse_pick_rows("K-1 | 章节 | [知识点] 含|竖线 标题 | ⬜ | 下次:2026-10-16")
check("_parse_pick_rows 标题含竖线", rows and rows[0]["id"] == "K-1"
      and rows[0]["status"] == "⬜" and rows[0]["due"] == "2026-10-16" and "竖线" in rows[0]["title"])
sel = L._select_chunks([("A.md", ["滑动窗口 双指针 去重", "无关内容一"]), ("B.md", ["滑动窗口模板"])], "滑动窗口怎么去重")
check("_select_chunks 关键词打分选段", sel and sel[0]["score"] >= 2 and "滑动窗口" in sel[0]["text"])

# ---------- AI 劫持（v20/v27 手法：不覆盖用户密钥，测完恢复 base_url/model/active） ----------
s, full = call("GET", "/api/config")
prov = next((p for p in full["ai"]["providers"] if p["has_key"] and p["enabled"]), None)
saved = None
saved_folder = full["leetcode"].get("folder", "")
if prov:
    saved = (prov["name"], prov["base_url"], prov["model"],
             full["ai"]["embedding"], full["ai"]["active"])
    call("PUT", "/api/config", {"ai": {"providers": [
        {"name": prov["name"], "base_url": MOCK, "model": "mock-a"}]}})
    call("PUT", "/api/config", {"ai": {"active": prov["name"]}})
AI_ON = bool(prov)

# ---------- 夹具：临时力扣文件夹（lj.py init + add 真实体系） ----------
tmp = Path(tempfile.mkdtemp(prefix="v30lc_"))
(tmp / "题解笔记.md").write_text("# 两数之和\n\n哈希表先查后存，避免重复使用当前元素。\n", encoding="utf-8")
lj_src = ROOT / "app" / "services" / "_learning_skill" / "lj.py"
(tmp / "learning" / "scripts").mkdir(parents=True)
shutil.copy(lj_src, tmp / "learning" / "scripts" / "lj.py")
_lj = str(tmp / "learning" / "scripts" / "lj.py")
_r = subprocess.run([sys.executable, "-X", "utf8", _lj, "init", "--course", "LeetCode 刷题", "--open"],
                    capture_output=True, encoding="utf-8", errors="ignore")
assert _r.returncode == 0, f"lj init 失败: {_r.stderr[:200]}"
for i, (chapter, tag, title, q, a) in enumerate([
        ("双指针", "知识点", "两数之和先查后存", "为什么先查 target-x 再存 x？", "避免元素重复使用自己。"),
        ("双指针", "Bug", "窗口左边界回退", "无重复子串左边界为什么只能前进？", "回退会重新纳入已排除字符。"),
        ("栈", "设计", "括号匹配用栈", "为什么括号匹配天然适合栈？", "最近未匹配的左括号最先需要配对。")]):
    card = json.dumps({"chapter": chapter, "type": tag, "title": title, "q": q, "a": a,
                       "code": "", "point": "p", "summary": "s", "ref": "LC", "lang": "python"},
                      ensure_ascii=False)
    _r = subprocess.run([sys.executable, "-X", "utf8", _lj, "add", card],
                        capture_output=True, encoding="utf-8", errors="ignore")
    assert _r.returncode == 0, f"lj add 失败: {_r.stderr[:200]}"

print("== 1. 文件夹绑定与状态 ==")
s, r = call("PUT", "/api/config", {"leetcode": {"folder": str(tmp)}})
check("绑定临时文件夹", s == 200)
s, r = call("GET", "/api/leetcode/folder")
check("状态:绑定且存在", r.get("bound") and r.get("exists"))
check("状态:识别 learning 体系", r.get("has_learning") is True, json.dumps(r, ensure_ascii=False))
check("状态:卡数/章节", r.get("cards") == 3 and r.get("chapters") >= 1)
check("状态:待复习=3（新卡明日到期不计今日，池按非✅计）", r.get("due") == 0 and r.get("cards") == 3)

print("== 2. 问 AI（F31） ==")
s, r = call("POST", "/api/leetcode/ask", {"question": "  "})
check("问AI空问题 400", s == 400)
s, r = call("POST", "/api/leetcode/ask", {"question": "两数之和为什么要先查再存？"})
check("问AI走 AI", r.get("ai_used") is True, json.dumps(r, ensure_ascii=False)[:200])
src_names = [x.get("name") for x in r.get("sources", []) if x.get("name")]
check("问AI标注来源文件", "题解笔记.md" in src_names or "学习笔记.md" in src_names, str(src_names))
check("问AI标注卡片编号", any(x.get("card") for x in r.get("sources", [])))

print("== 3. 到期复习（F32） ==")
s, r = call("POST", "/api/leetcode/review/pick", {"n": 2})
check("挑卡返回2张", len(r.get("cards", [])) == 2, json.dumps(r, ensure_ascii=False)[:200])
c1 = r["cards"][0]
check("卡片带问句（非标题兜底）", len(c1.get("q", "")) > 4 and c1["q"].endswith("？"))
check("卡片带参考要点", len(c1.get("ref", "")) > 10)
s, r = call("POST", "/api/leetcode/review/grade", {"question": "", "answer": "x"})
check("判分空作答 400", s == 400)
s, r = call("POST", "/api/leetcode/review/grade", {"question": c1["q"], "answer": "先查后存", "ref": c1["ref"]})
check("判分 verdict=pass（mock）", r.get("verdict") == "pass", json.dumps(r, ensure_ascii=False))
s, r = call("POST", "/api/leetcode/review/mark", {"id": c1["id"], "result": "bad"})
check("打卡非法结果被拒", s >= 400)
s, r = call("POST", "/api/leetcode/review/mark", {"id": c1["id"], "result": "pass"})
check("打卡 pass 成功", r.get("ok") is True and "阶段" in r.get("msg", ""), json.dumps(r, ensure_ascii=False))
rv = (tmp / "learning" / "复习清单.md").read_text(encoding="utf-8")
row = next((l for l in rv.splitlines() if l.strip().startswith(f"| {c1['id']} ")), "")
check("复习清单回写 ✅ 阶段1", "✅" in row and "| 1 |" in row, row)
_, again = call("POST", "/api/leetcode/review/pick", {"n": 5})
c2 = again["cards"][-1]
check("pass 卡移出待复习池", all(x["id"] != c1["id"] for x in again["cards"]))
s, r = call("POST", "/api/leetcode/review/mark", {"id": c2["id"], "result": "fail"})
check("打卡 fail 成功", r.get("ok") is True)
rv = (tmp / "learning" / "复习清单.md").read_text(encoding="utf-8")
check("复习清单存在 🔄 重置行", "🔄" in rv)

print("== 4. 边界：无 learning 体系 / 未绑定 ==")
tmp_plain = Path(tempfile.mkdtemp(prefix="v30plain_"))
(tmp_plain / "notes.md").write_text("# 笔记\n\n只有普通笔记。\n", encoding="utf-8")
call("PUT", "/api/config", {"leetcode": {"folder": str(tmp_plain)}})
s, r = call("GET", "/api/leetcode/folder")
check("普通文件夹: has_learning=false", r.get("bound") and r.get("exists") and r.get("has_learning") is False)
s, r = call("POST", "/api/leetcode/review/pick", {"n": 3})
check("普通文件夹: 复习明确报错", s >= 400 and "lj.py" in (r.get("error") or ""), json.dumps(r, ensure_ascii=False))
s, r = call("POST", "/api/leetcode/ask", {"question": "这里有什么笔记？"})
check("普通文件夹: 问AI仍可用", r.get("ai_used") is True)
call("PUT", "/api/config", {"leetcode": {"folder": ""}})
s, r = call("GET", "/api/leetcode/folder")
check("解绑: bound=false", r.get("bound") is False)
s, r = call("POST", "/api/leetcode/review/pick", {"n": 3})
check("未绑定: 复习报错", s >= 400)

# ---------- 面经收藏删除（端点 v1.19 已有，v1.20 前端补键；此处回归端点） ----------
print("== 5. 面经收藏增删 ==")
s, r = call("POST", "/api/kb/clips", {"title": "v30临时收藏", "link": "https://example.com/v30"})
check("收藏创建", s == 201 and r.get("id"))
cid = r.get("id")
s, r = call("GET", "/api/kb/clips")
check("收藏列表含新条目", any(c["id"] == cid for c in r.get("items", [])))
s, r = call("DELETE", f"/api/kb/clips/{cid}")
check("收藏删除成功", r.get("ok") is True)
s, r = call("GET", "/api/kb/clips")
check("删除后列表为空", not any(c["id"] == cid for c in r.get("items", [])))

# ---------- 恢复现场 ----------
call("PUT", "/api/config", {"leetcode": {"folder": saved_folder}})
if saved:
    # 恢复用户真实 AI 配置（不传 api_key → 真实密钥不受影响）
    call("PUT", "/api/config", {"ai": {"providers": [
        {"name": saved[0], "base_url": saved[1], "model": saved[2]}],
        "embedding": {"model": saved[3]}, "active": saved[4]}})
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(tmp_plain, ignore_errors=True)

print(f"\n===== 通过 {len(PASS)} / 失败 {len(FAIL)} =====")
if FAIL:
    print("失败项：", FAIL)
sys.exit(1 if FAIL else 0)
