# -*- coding: utf-8 -*-
"""textkit —— 核心层共享文本工具（v1.21 自 kb/grad/leetcode 三域下沉；ARCHITECTURE v0.2）。

纯函数、无状态、零业务概念：只被上层调用，不调用任何模块（含 core 内部）。
services 向下 import 合法（依赖方向单向 services → core）。

- 抽取：docx/pptx 标准库解包、pdf 可选 pypdf（缺组件返回 None/空，功能降级不报错）
- 分块：按空行聚段成 ~size 字块，超长段落硬切
- 选段：查询词项（中文二字组+英文词）打分 + 预算控制；无 query 时轮转各文件取段
- 解析：AI 出题 JSON 数组容错解析
"""
import html
import io
import json
import re
import zipfile
from pathlib import Path

TEXT_EXTS = {".md", ".txt", ".markdown", ".py", ".java", ".c", ".cc", ".cpp",
             ".h", ".hpp", ".sql", ".r", ".m", ".csv", ".json", ".log", ".go", ".rs"}
PER_FILE_CAP = 60000     # 单文件抽取字符上限


def _xml_runs_to_text(xml: str) -> str:
    """pptx 幻灯片 XML（DrawingML）→ 文本：a:t 文本运行拼接，段落换行。"""
    xml = re.sub(r"</a:p>", "\n", xml)
    text = "".join(re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)) or re.sub(r"<[^>]+>", "", xml)
    return html.unescape(text)


def docx_text(data: bytes) -> str:
    """标准库解包 .docx 提取正文（word/document.xml 按段落还原换行）。"""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def pptx_text(data: bytes) -> str:
    """逐张幻灯片抽文本（slideN.xml 的 a:t 文本运行），页间空行分隔。"""
    slides = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        names.sort(key=lambda n: int(re.search(r"(\d+)", n).group(1)))
        for n in names:
            t = _xml_runs_to_text(z.read(n).decode("utf-8", "ignore")).strip()
            if t:
                slides.append(t)
    return "\n\n".join(slides)


def pdf_text(data: bytes) -> str | None:
    """pypdf 抽取（可选依赖）：未安装或解析失败返回 None，调用方据此降级。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    except Exception:
        return None


def extract_text(path: Path) -> str:
    """尽力抽取文本文件正文：能解的解，解不出返回空串（按仅文件名处理）。"""
    try:
        ext = path.suffix.lower()
        if ext in TEXT_EXTS:
            return path.read_text(encoding="utf-8", errors="ignore")[:PER_FILE_CAP]
        if ext == ".docx":
            return docx_text(path.read_bytes())[:PER_FILE_CAP]
        if ext == ".pptx":
            return pptx_text(path.read_bytes())[:PER_FILE_CAP]
        if ext == ".pdf":
            return (pdf_text(path.read_bytes()) or "")[:PER_FILE_CAP]
    except Exception:
        return ""
    return ""


def chunks_of(text: str, size=500):
    """按空行聚段成 ~size 字块，超长段落硬切。"""
    out, buf = [], ""
    for p in re.split(r"\n{2,}", text):
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 1 <= size:
            buf = (buf + "\n" + p).strip()
            continue
        if buf:
            out.append(buf)
        while len(p) > size:
            out.append(p[:size])
            p = p[size:]
        buf = p
    if buf:
        out.append(buf)
    return out


def terms_of(q: str) -> set:
    """查询词项：中文二字组 + 英文/数字词（小写）。"""
    q = q.lower()
    bi = {s[i:i + 2] for s in re.findall(r"[\u4e00-\u9fff]+", q) for i in range(len(s) - 1)}
    en = set(re.findall(r"[a-z0-9_+#.\-]{2,}", q))
    return bi | en


def select_chunks(files_text: list, query: str, k=8, budget=6000):
    """[(name, chunks)] → 选段喂 AI。

    有 query：按词项命中数打分、降序取（全零分时保底按原序），预算 budget 字、至多 k 块；
    无 query（出题/展示）：轮转各文件取段，保证文件间均衡。
    返回 [{name, text, score}]。
    """
    terms = terms_of(query) if query else None
    scored, per_file = [], []
    for name, cs in files_text:
        if terms:
            for c in cs:
                low = c.lower()
                s = sum(1 for t in terms if t in low)
                scored.append({"name": name, "text": c, "score": s})
        else:
            per_file.append((name, cs))
    picked, left = [], budget
    if terms:
        scored.sort(key=lambda x: -x["score"])
        scored = [c for c in scored if c["score"] > 0] or scored
        for c in scored:
            if left - len(c["text"]) < 0 or len(picked) >= k:
                break
            picked.append(c)
            left -= len(c["text"])
    else:
        while len(picked) < k and any(cs for _, cs in per_file):
            for name, cs in per_file:
                if cs and len(picked) < k:
                    c = cs.pop(0)
                    if left - len(c) >= 0:
                        picked.append({"name": name, "text": c, "score": 0})
                        left -= len(c)
    return picked


def parse_quiz_json(reply: str, n: int):
    """AI 出题回复 → [{"q": ...}]；解析不出返回 []（调用方自行降级）。"""
    m = re.search(r"\[.*\]", reply, re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    out = []
    for x in arr if isinstance(arr, list) else []:
        q = x.get("q") if isinstance(x, dict) else x
        if isinstance(q, str) and q.strip():
            out.append({"q": q.strip()})
        if len(out) >= n:
            break
    return out
