# -*- coding: utf-8 -*-
"""v1.17 验收：课程 AI 问答（F27）/ AI 考我（F28）/ 学习助手进驻课程文件夹（F29）。

自建本地 mock OpenAI 服务（内容感知：按 system 提示分流出题 JSON/判分/普通回答），
测完恢复用户真实 AI 配置。课程文件夹用系统临时目录，测完连同磁盘目录一并清理；
学习助手安装物（.zcode/.agents/learning）随临时目录消失，学习笔记永不覆盖单独验证。
"""
import io
import json
import re
import shutil
import sqlite3
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []
ROOT = Path(__file__).resolve().parent.parent


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


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


# ---------- 本地 mock OpenAI 服务（按 system 提示分流回复） ----------
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

    def do_GET(self):
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(n) or b"{}")
        if self.path.endswith("/chat/completions"):
            msgs = payload.get("messages") or []
            sys_msg = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
            user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
            if "评判" in sys_msg:                      # F28 判分
                content = "过\n要点命中，条理清晰。"
            elif "JSON 数组" in sys_msg:               # F28 出题
                mnum = re.search(r"出题数量：(\d+)", user)
                k = int(mnum.group(1)) if mnum else 3
                content = json.dumps(
                    [{"q": f"mock第{i + 1}题：请简述课程资料中的重点{i + 1}"} for i in range(k)],
                    ensure_ascii=False)
            elif "AI 考我坏例" in user:                 # 出题解析失败 → 降级
                content = "这不是 JSON"
            else:                                      # F27 问答
                content = "【mock】依据课程资料：过拟合=训练集表现好但泛化差，缓解靠正则化与早停。"
            return self._json({
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70}})
        if self.path.endswith("/embeddings"):
            return self._json({"error": "embed not supported by mock"}, 500)
        self._json({"error": "not found"}, 404)


srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
MOCK = f"http://127.0.0.1:{srv.server_address[1]}/v1"
threading.Thread(target=srv.serve_forever, daemon=True).start()

# ---------- 课程临时文件夹：md + pptx（零依赖可解析） ----------
tmpA = Path(tempfile.mkdtemp(prefix="v27courseA_"))
tmpB = Path(tempfile.mkdtemp(prefix="v27courseB_"))
(tmpA / "讲义.md").write_text(
    "# 机器学习讲义\n\n## 过拟合\n\n过拟合指模型在训练集上表现很好，但在新样本上泛化差。"
    "判断依据是训练误差与验证误差的差距：训练误差低而验证误差高即为过拟合。\n\n"
    "缓解方法：正则化（L1/L2）、早停、数据增强、Dropout、扩大训练集。\n\n"
    "## 偏差与方差\n\n偏差刻画模型对真实规律的拟合能力不足，方差刻画模型对训练数据扰动的敏感程度。"
    "偏差高对应欠拟合，方差高对应过拟合。集成方法里 Bagging 主要降方差，Boosting 主要降偏差。\n\n"
    "## 正则化\n\nL1 正则（Lasso）把部分权重压成零，产生稀疏解，可用于特征选择。"
    "L2 正则（Ridge）让权重整体变小但不为零，使模型更平滑。正则强度用验证集调。\n\n"
    "## 决策树\n\n常用划分准则有信息增益、增益率与基尼指数。剪枝分预剪枝与后剪枝，"
    "预剪枝可能欠拟合，后剪枝通常泛化更好。\n\n"
    "## 支持向量机\n\n硬间隔要求线性可分，软间隔引入松弛变量容忍少量越界样本。"
    "核技巧把样本隐式映射到高维：线性核、多项式核、RBF 核各有适用场景。\n\n"
    "## 集成学习\n\nBagging 并行训练再投票，代表是随机森林；Boosting 串行纠错，"
    "代表有 AdaBoost、GBDT、XGBoost。两者都能显著降低单模型的方差。\n", encoding="utf-8")
pptx_buf = io.BytesIO()
with zipfile.ZipFile(pptx_buf, "w") as z:
    z.writestr("ppt/slides/slide1.xml", "<p:sld><a:p><a:r><a:t>监督学习流程</a:t></a:r></a:p></p:sld>")
    z.writestr("ppt/slides/slide2.xml", "<p:sld><a:p><a:r><a:t>交叉验证：k 折把数据分成 k 份轮流做验证</a:t></a:r></a:p></p:sld>")
(tmpA / "课件.pptx").write_bytes(pptx_buf.getvalue())

# ---------- AI 劫持（沿用 v20 手法：不覆盖用户密钥，测完恢复） ----------
s, full = call("GET", "/api/config")
prov = next((p for p in full["ai"]["providers"] if p["has_key"] and p["enabled"]), None)
assert prov, "没有已存密钥的档案（本测试需已配置 AI，供劫持到 mock）"
s2, full2 = call("GET", "/api/config")
saved = (prov["name"], prov["base_url"], prov["model"], full2["ai"]["embedding"],
         full2["ai"]["active"])
call("PUT", "/api/config", {"ai": {"providers": [
    {"name": prov["name"], "base_url": MOCK, "model": "mock-a"}]}})
call("PUT", "/api/config", {"ai": {"active": prov["name"]}})

CID = None
try:
    print("== 1. 建课自动安装学习助手（F29） ==")
    s, r = call("POST", "/api/grad/courses",
                {"name": "v27测试课-勿留", "folder_path": str(tmpA)})
    check("建课成功", s == 201)
    CID = r["id"]
    s, d = call("GET", f"/api/grad/courses/{CID}")
    check("详情返回 skill_installed=true", s == 200 and d["course"]["skill_installed"] is True)
    check("SKILL.md 已装 .zcode 落点",
          (tmpA / ".zcode" / "skills" / "learning-assistant" / "SKILL.md").is_file())
    check("SKILL.md 已装 .agents 落点",
          (tmpA / ".agents" / "skills" / "learning-assistant" / "SKILL.md").is_file())
    check("lj.py 装进 learning/scripts", (tmpA / "learning" / "scripts" / "lj.py").is_file())
    jf = ["学习配置.md", "学习笔记.md", "进度表.md", "复习清单.md"]
    check("learning 四件套齐全", all((tmpA / "learning" / f).is_file() for f in jf))
    cfg = (tmpA / "learning" / "学习配置.md").read_text(encoding="utf-8")
    check("学习配置带课程名+开放式", "v27测试课-勿留" in cfg and "开放式章节**：true" in cfg)
    skill = (tmpA / ".zcode" / "skills" / "learning-assistant" / "SKILL.md").read_text(encoding="utf-8")
    check("skill 触发规则=主动学习才启用",
          "我要学习了" in skill and "不要主动启用" in skill)
    check("文件夹文件被列出（md+pptx，安装物不进复习清单）",
          {f["name"] for f in d["files"]} == {"讲义.md", "课件.pptx"})

    print("== 2. 重装幂等：笔记永不覆盖 ==")
    note = tmpA / "learning" / "学习笔记.md"
    note.write_text(note.read_text(encoding="utf-8") + "\n<!-- v27 用户痕迹 -->\n", encoding="utf-8")
    s, r = call("POST", f"/api/grad/courses/{CID}/skill")
    check("重装成功且未重新 init", s == 200 and r.get("inited") is False)
    check("用户笔记内容保留", "v27 用户痕迹" in note.read_text(encoding="utf-8"))

    print("== 3. 课程 AI 问答（F27） ==")
    s, r = call("POST", f"/api/grad/courses/{CID}/ask", {"question": "过拟合是什么，怎么缓解？"})
    check("问答走通 mock", s == 200 and r.get("ai_used") is True)
    check("回答来自 mock 通道", "mock" in r.get("answer", ""))
    srcs = {x["name"] for x in r.get("sources", [])}
    check("来源标注文件名", "讲义.md" in srcs)
    s, r = call("POST", f"/api/grad/courses/{CID}/ask", {"question": "交叉验证怎么做"})
    srcs = {x["name"] for x in r.get("sources", [])}
    check("pptx 抽取可命中（关键词选段）", "课件.pptx" in srcs)
    s, r = call("POST", f"/api/grad/courses/{CID}/ask", {"question": ""})
    check("空问题→400", s == 400)
    con = sqlite3.connect(ROOT / "data" / "workbench.db", timeout=5)
    n_cached = con.execute("SELECT COUNT(*) FROM grad_file_text WHERE course_id=?",
                           (CID,)).fetchone()[0]
    con.close()
    check("抽取文本已缓存（mtime 缓存表）", n_cached >= 2)

    print("== 4. AI 考我（F28） ==")
    s, r = call("POST", f"/api/grad/courses/{CID}/quiz", {"n": 3})
    check("出题 3 道·AI 通道", s == 200 and len(r.get("questions", [])) == 3
          and r.get("ai_used") is True)
    check("题目结构含 q", all("q" in x for x in r["questions"]))
    s, r = call("POST", f"/api/grad/courses/{CID}/quiz/grade",
                {"question": "L1 和 L2 的区别？", "answer": "L1 稀疏 L2 平滑", "ref": "L1 稀疏解"})
    check("判分 verdict=pass + 点评", s == 200 and r.get("verdict") == "pass"
          and r.get("comment") and r.get("ai_used") is True)
    s, r = call("POST", f"/api/grad/courses/{CID}/quiz/grade", {"question": "q", "answer": ""})
    check("空作答→400", s == 400)
    import sys
    sys.path.insert(0, str(ROOT))
    from app.services.grad import _parse_quiz_json
    check("出题解析纯函数：坏回复→[]（触发降级）", _parse_quiz_json("这不是JSON", 3) == [])
    check("出题解析纯函数：夹在垃圾文本里可提取",
          [x["q"] for x in _parse_quiz_json('前缀[{"q":"a"}]后缀', 3)] == ["a"])

    print("== 5. 降级路径（AI 未配置） ==")
    call("PUT", "/api/config", {"ai": {"active": None}})
    s, r = call("POST", f"/api/grad/courses/{CID}/ask", {"question": "过拟合怎么缓解"})
    check("问答降级：给出资料参考段落", s == 200 and r.get("ai_used") is False
          and "AI 未配置" in r.get("answer", "") and "过拟合" in r.get("answer", ""))
    s, r = call("POST", f"/api/grad/courses/{CID}/quiz", {"n": 3})
    check("出题降级：片段自测题带 ref", s == 200 and r.get("ai_used") is False
          and len(r["questions"]) == 3 and all(x.get("ref") for x in r["questions"]))
    s, r = call("POST", f"/api/grad/courses/{CID}/quiz/grade",
                {"question": "q", "answer": "a", "ref": "r"})
    check("判分降级：verdict=null 交前端自评", s == 200 and r.get("verdict") is None
          and r.get("ai_used") is False)

    print("== 6. 未绑课/换绑自动安装（F29） ==")
    s, r = call("POST", "/api/grad/courses", {"name": "v27无夹课-勿留"})
    CID2 = r["id"]
    s, d = call("GET", f"/api/grad/courses/{CID2}")
    check("未绑课 skill_installed=false", s == 200 and d["course"]["skill_installed"] is False)
    s, r = call("POST", f"/api/grad/courses/{CID2}/skill")
    check("未绑课手动安装→400 友好提示", s == 400 and "文件夹" in r.get("error", ""))
    s, r = call("POST", f"/api/grad/courses/{CID2}/quiz", {"n": 3})
    check("未绑课出题→400 友好提示", s == 400 and "资料" in r.get("error", ""))
    s, r = call("PUT", f"/api/grad/courses/{CID2}", {"folder_path": str(tmpB)})
    s, d = call("GET", f"/api/grad/courses/{CID2}")
    check("换绑后自动安装", s == 200 and d["course"]["skill_installed"] is True
          and (tmpB / "learning" / "学习配置.md").is_file()
          and "v27无夹课-勿留" in (tmpB / "learning" / "学习配置.md").read_text(encoding="utf-8"))

    print("== 7. 用量记账与新端点回归 ==")
    call("PUT", "/api/config", {"ai": {"active": saved[0]}})
    s, r = call("POST", f"/api/grad/courses/{CID}/ask", {"question": "课程问答记账检查"})
    check("记账恢复 mock 通道后仍可用", s == 200 and r.get("ai_used") is True)
    s, r = call("GET", "/api/usage/summary")
    check("功能标签=课程问答入账", any(f["feature"] == "课程问答" for f in r.get("by_feature", [])))
finally:
    # 恢复用户真实 AI 配置（不传 api_key → 真实密钥不受影响）
    if saved:
        call("PUT", "/api/config", {"ai": {"providers": [
            {"name": saved[0], "base_url": saved[1], "model": saved[2]}],
            "embedding": {"model": saved[3]}, "active": saved[4]}})
    # 课程 + 磁盘临时目录清理
    for cid in (CID, globals().get("CID2")):
        if cid:
            call("DELETE", f"/api/grad/courses/{cid}")
    srv.shutdown()

s, r = call("GET", "/api/grad/courses")
left = [c for c in r["courses"] if "v27" in c["name"]]
check("测试课程已清理", not left)
shutil.rmtree(tmpA, ignore_errors=True)
shutil.rmtree(tmpB, ignore_errors=True)

con = sqlite3.connect(ROOT / "data" / "workbench.db", timeout=5)
# 只查本测试两个课程 id（真实课程的问答缓存合法存在，不能断言全表为 0）
_test_ids = [i for i in (CID, globals().get("CID2")) if i]
marks = ",".join("?" * len(_test_ids))
n_left = con.execute(f"SELECT COUNT(*) FROM grad_file_text WHERE course_id IN ({marks})",
                     _test_ids).fetchone()[0]
con.execute("DELETE FROM ai_usage WHERE model='mock-a'")
con.commit()
con.close()
check("grad_file_text 无泄漏（课程删则缓存删）", n_left == 0)

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
