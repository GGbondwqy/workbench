# -*- coding: utf-8 -*-
"""v1.9 验收：题库扩充（听力/阅读各≥4套 + 新原创套可判分）/ 音频双通道端点 / 考试日卡片数据链路。
自清理：临时音频删除、config 恢复原值。"""
import json
import urllib.request
import urllib.error
from pathlib import Path

B = "http://127.0.0.1:8787"
PASS, FAIL = [], []


def call(method, path, body=None, headers=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(B + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(), dict(e.headers)
        except Exception:
            return e.code, b"", {}


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


print("== 1. 题库扩充 ==")
s, raw, _ = call("GET", "/api/ielts/bank")
items = json.loads(raw)["items"]
n_listen = sum(1 for i in items if i["subject"] == "listening")
n_read = sum(1 for i in items if i["subject"] == "reading")
check("听力≥4套", n_listen >= 4)
check("阅读≥4套", n_read >= 4)
check("无测试残留题组", not any("v13导入测试" in i["id"] for i in items))

print("== 2. 新原创听力套 ==")
s, raw, _ = call("GET", "/api/ielts/bank/b-listen-3")
set3 = json.loads(raw)
check("b-listen-3 可取", s == 200 and set3["subject"] == "listening"
      and sum(len(x["questions"]) for x in set3["sections"]) == 7)
s, raw, _ = call("GET", "/api/ielts/bank/b-listen-4")
set4 = json.loads(raw)
check("b-listen-4 可取", s == 200 and set3 is not None and set4["subject"] == "listening")
# 公开收集题抽查
s, raw, _ = call("GET", "/api/ielts/bank/public-read-turtle-navigation")
tur = json.loads(raw)
check("公开题组·海龟导航可取", s == 200 and tur.get("source") == "public"
      and sum(len(x["questions"]) for x in tur["sections"]) == 7)
# 判分抽查：b-listen-3 全对提交（1=25, 2=C, 3=2, 4=C, 5=14, 6=380, 7=B）
s, raw, _ = call("POST", "/api/ielts/bank/b-listen-3/submit", {
    "answers": {"1": "25", "2": "C", "3": "2", "4": "C", "5": "14", "6": "380", "7": "B"}})
r = json.loads(raw)
check("b-listen-3 全对判分", s == 200 and r["score"] == 100)
# 半对提交验证 blank 多候选（3=two 也算对；5=fourteenth 也算对）
s, raw, _ = call("POST", "/api/ielts/bank/b-listen-3/submit", {
    "answers": {"1": "25", "2": "A", "3": "two", "4": "20", "5": "fourteenth", "6": "38", "7": "B"}})
r = json.loads(raw)
check("blank 多候选判分", s == 200 and r["correct"] == 4)

print("== 3. 音频双通道端点 ==")
s, raw, _ = call("GET", "/api/ielts/audio/b-listen-3/0")
check("无本机音频→404（TTS降级信号）", s == 404)
aud_dir = Path(__file__).resolve().parent.parent / "data" / "ielts_audio"
aud_dir.mkdir(parents=True, exist_ok=True)
fake = aud_dir / "b-listen-3-0.mp3"
fake.write_bytes(b"ID3" + b"\x00" * 4096)
shared = aud_dir / "b-listen-4.mp3"
shared.write_bytes(b"ID3" + b"\x00" * 128)
try:
    s, raw, h = call("GET", "/api/ielts/audio/b-listen-3/0")
    check("本机音频→200二进制", s == 200 and raw.startswith(b"ID3")
          and h.get("Content-Type") == "audio/mpeg" and h.get("Accept-Ranges") == "bytes")
    s, raw, h = call("GET", "/api/ielts/audio/b-listen-3/0", headers={"Range": "bytes=4-103"})
    check("Range请求→206", s == 206 and len(raw) == 100
          and h.get("Content-Range") == f"bytes 4-103/{fake.stat().st_size}")
    s, raw, _ = call("GET", "/api/ielts/audio/b-listen-4/2")
    check("整套共用命名 {id}.mp3", s == 200 and raw.startswith(b"ID3"))
finally:
    fake.unlink(missing_ok=True)
    shared.unlink(missing_ok=True)
for bad in ("..%2F..%2Fconfig.json", "..%5Cserver.py"):
    s, _, _ = call("GET", "/api/ielts/audio/" + bad + "/0")
    check(f"路径穿越拦截 {bad[:12]}…", s == 404)

print("== 4. 考试日卡片数据链路（含恢复） ==")
s, raw, _ = call("GET", "/api/ielts/config")
orig = json.loads(raw)
saved_exam = orig.get("exam_date")
saved_target = orig.get("target_overall")
try:
    call("PUT", "/api/ielts/config", {"exam_date": "2027-05-15"})
    s, raw, _ = call("GET", "/api/ielts/config")
    cfg = json.loads(raw)
    check("设定考试日→倒计时数字", cfg["days_left"] is not None and cfg["days_left"] > 200)
    call("PUT", "/api/ielts/config", {"exam_date": None})
    s, raw, _ = call("GET", "/api/ielts/config")
    check("清除考试日→倒计时为空", json.loads(raw)["days_left"] is None)
finally:
    call("PUT", "/api/ielts/config", {"exam_date": saved_exam, "target_overall": saved_target})

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
