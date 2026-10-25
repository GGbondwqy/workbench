# -*- coding: utf-8 -*-
"""知识库 RAG 辅助（kb 域内部使用，非独立服务）：

- 上下文增强分块：按 Markdown 小节切分，段落聚合到目标长度（DESIGN F22），
  块文本自带「文章标题 · 小节名」前缀，embedding 与检索都带上下文
- 向量工具：float32 BLOB 序列化 / L2 归一化 / 余弦（候选集≤64，纯 Python 足够快）
"""
import math
import re
import struct
from array import array

_HEADING = re.compile(r"^(#{1,4})\s+(.+)$", re.M)


def chunk_article(title: str, body: str, target=450, max_len=700) -> list[dict]:
    """切分一篇文章 → [{seq, heading, text}]。text 为块正文（不含前缀）。"""
    # 去 frontmatter，按标题分节（无标题文章整体为一节）
    body = re.sub(r"^---.*?---\s*", "", body, flags=re.S)
    sections: list[tuple[str, str]] = []
    parts = _HEADING.split(body)   # [前文, level, 名, 内容, level, 名, 内容…]
    if len(parts) == 1:
        sections.append(("", body))
    else:
        if parts[0].strip():
            sections.append(("", parts[0]))
        for i in range(1, len(parts) - 2, 3):
            sections.append((parts[i + 1].strip(), parts[i + 2]))

    chunks = []
    for heading, sec_text in sections:
        paras = [p.strip() for p in re.split(r"\n\s*\n", sec_text) if p.strip()]
        # 长段落在句/行边界再细分
        pieces = []
        for p in paras:
            if len(p) <= max_len:
                pieces.append(p)
                continue
            lines = p.splitlines()
            cur = ""
            for ln in lines:
                if len(cur) + len(ln) + 1 > max_len and cur:
                    pieces.append(cur)
                    cur = ln
                else:
                    cur = f"{cur}\n{ln}".strip()
            if cur:
                pieces.append(cur)
        # 聚合到目标长度（块间自然边界，不做跨块重叠：前缀上下文已提供连续性）
        buf = ""
        for piece in pieces:
            if buf and len(buf) + len(piece) + 1 > target and len(buf) >= 120:
                chunks.append({"heading": heading, "text": buf})
                buf = piece
            else:
                buf = f"{buf}\n{piece}".strip()
        if buf.strip():
            chunks.append({"heading": heading, "text": buf})

    for i, c in enumerate(chunks):
        c["seq"] = i
    return chunks


def embed_text(title: str, heading: str, text: str) -> str:
    """块的 embedding 输入：标题 · 小节 + 正文（上下文增强分块）。"""
    prefix = title if not heading else f"{title} · {heading}"
    return f"{prefix}\n{text}"


def vec_to_blob(vec: list[float]) -> bytes:
    return array("f", vec).tobytes()


def blob_to_vec(blob: bytes) -> array:
    a = array("f")
    a.frombytes(blob)
    return a


def l2_normalize(vec) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine(a, b) -> float:
    """输入均已归一化 → 点积即余弦。"""
    return sum(x * y for x, y in zip(a, b))
