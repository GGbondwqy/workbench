# -*- coding: utf-8 -*-
"""知识库域 v2（DESIGN v2.0）：多库实例 / wiki 双链 / 知识图谱 / 四入口入库 / 文件解析。

库实例：
- bagu（八股）：只读根 = config.kb.path；可写根 = data/kb_custom（自建文章）
- mianjing（面经）：可写根 = data/kb_mianjing
版权边界不变：第三方内容只在库外目录，data/ 不入 git。
"""
import re
import json
import hashlib
import threading
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

from app.core.registry import AppContext
from app.core.textkit import docx_text as _docx_to_text, pdf_text as _pdf_to_text  # v1.21 下沉共享
from app.core.timeutil import now
from app.services import kb_rag

MIGRATIONS = [
    # 0011 为 v1 建表（全新库也需要；老库已应用会自动跳过）
    ("0011_kb", """
        CREATE TABLE IF NOT EXISTS kb_articles (
            relpath  TEXT PRIMARY KEY,
            title    TEXT NOT NULL,
            category TEXT DEFAULT '',
            source   TEXT DEFAULT '',
            mtime    TEXT DEFAULT ''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
            relpath UNINDEXED, title, body, tokenize='unicode61'
        );
    """),
    ("0012_kb_v2", """
        ALTER TABLE kb_articles ADD COLUMN library TEXT NOT NULL DEFAULT 'bagu';
        CREATE TABLE IF NOT EXISTS kb_edges (
            src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL,
            weight INTEGER DEFAULT 1,
            PRIMARY KEY (src, dst, type)
        );
        CREATE TABLE IF NOT EXISTS kb_edge_blacklist (
            src TEXT NOT NULL, dst TEXT NOT NULL, PRIMARY KEY (src, dst)
        );
        CREATE TABLE IF NOT EXISTS kb_clips (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            link  TEXT DEFAULT '',
            tags  TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    """),
    # 初次升级：把已有文章归入 bagu 库
    ("0013_kb_lib_init", "UPDATE kb_articles SET library='bagu' WHERE library='';"),
    ("0021_kb_rag", """
        CREATE TABLE IF NOT EXISTS kb_chunks (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            relpath TEXT NOT NULL,
            seq     INTEGER NOT NULL,
            title   TEXT DEFAULT '',
            heading TEXT DEFAULT '',
            text    TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_kb_chunks_rel ON kb_chunks(relpath);
        CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(
            chunk_id UNINDEXED, text, tokenize='unicode61'
        );
        CREATE TABLE IF NOT EXISTS kb_chunk_vec (
            chunk_id INTEGER PRIMARY KEY,
            model    TEXT NOT NULL,
            dim      INTEGER NOT NULL,
            vec      BLOB NOT NULL
        );
    """),
]

_CJK = re.compile(r'([\u4e00-\u9fff])')
_WIKILINK = re.compile(r'\[\[([^\]]+)\]\]')

# 中文停用词（bigram 过滤用）
_STOP_CHARS = set('的了呢吧啊呀么是与在有好很不这那个也都被把和跟如果但其实于是就还要上下中大小多多少没无不要自己我们你们他们这那怎么为什么因为所以对于通过可以能够需要进去出来时候东西事情问题方面进行')
_EN_STOP = {"the", "a", "an", "of", "to", "and", "in", "is", "it", "for", "on", "as",
            "with", "by", "or", "be", "are", "this", "that", "from", "at", "其"}


def _tokenize_zh(text: str) -> str:
    return _CJK.sub(r'\1 ', text)


def _extract_keywords(title: str, body: str, top=10):
    """标题 bigram/英文词 权重×3 + 正文高频；供共现边计算。"""
    def words(s):
        en = re.findall(r'[A-Za-z]{3,}', s)
        zh_segs = re.findall(r'[\u4e00-\u9fff]+', s)
        bi = []
        for seg in zh_segs:
            bi += [seg[i:i + 2] for i in range(len(seg) - 1)]
        return [w for w in en if w.lower() not in _EN_STOP] + bi
    cnt = Counter(words(title) * 1 + words(body[:8000]))
    return {w for w, _ in cnt.most_common(top * 2)
            if not (len(w) == 2 and (w[0] in _STOP_CHARS or w[1] in _STOP_CHARS))} | set(words(title))


class KbService:
    name = "kb_service"
    LIBRARIES = {"bagu": "八股库", "mianjing": "面经库", "grad": "研究生知识库"}

    def __init__(self, ctx: AppContext):
        self._ctx = ctx
        self._roots = {}
        self._rag_progress = {"building": False, "done": 0, "total": 0,
                              "error": None, "started_at": None}

    # ---- 库与根 ----
    _WRITABLE_DIRS = {"bagu": "kb_custom", "mianjing": "kb_mianjing", "grad": "kb_grad"}

    def writable_root(self, library: str) -> Path:
        if library not in self._roots:
            p = self._ctx.data_dir / self._WRITABLE_DIRS.get(library, f"kb_{library}")
            p.mkdir(parents=True, exist_ok=True)
            self._roots[library] = p
        return self._roots[library]

    def readonly_root(self) -> Path | None:
        raw = self._ctx.config.get("kb", {}).get("path")
        if not raw:
            return None
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (self._ctx.root / p).resolve()
        return p if p.is_dir() else None

    def _resolve(self, library: str, relpath: str) -> Path | None:
        """可写库前缀路由（custom/=八股自建、mianjing/=面经、grad/=研究生），其余在 bagu 只读根。"""
        parts = relpath.split("/", 1)
        if len(parts) == 2 and parts[0] in ("custom", "mianjing", "grad"):
            lib = "bagu" if parts[0] == "custom" else parts[0]
            return (self.writable_root(lib) / parts[1]).resolve()
        if library == "bagu":
            root = self.readonly_root()
            if root:
                f = (root / relpath).resolve()
                if str(f).startswith(str(root.resolve())):
                    return f
        return None

    # ---- 扫描（F14 入口之一） ----
    def scan(self):
        n = 0
        root = self.readonly_root()
        if root:
            n += self._scan_dir(root, "bagu")
        n += self._scan_dir(self.writable_root("bagu"), "bagu", prefix="custom/")
        n += self._scan_dir(self.writable_root("mianjing"), "mianjing", prefix="mianjing/")
        n += self._scan_dir(self.writable_root("grad"), "grad", prefix="grad/")
        self.rebuild_graph()
        self.chunks_refresh()
        return {"imported": n, "total": self.count()}

    def _scan_dir(self, root: Path, library: str, prefix: str = ""):
        n = 0
        for f in root.rglob("*"):
            if f.suffix.lower() not in (".md", ".txt") or not f.is_file():
                continue
            rel = prefix + f.relative_to(root).as_posix()
            mtime = f.stat().st_mtime
            ex = self._ctx.db.query_one(
                "SELECT mtime FROM kb_articles WHERE relpath=?", (rel,))
            if ex and ex["mtime"] and float(ex["mtime"]) == mtime:
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            meta = self._parse_fm(text)
            self._upsert_article(rel, meta.get("title") or f.stem,
                                 meta.get("category", ""), meta.get("source", ""),
                                 str(mtime), library, text)
            n += 1
        return n

    def _upsert_article(self, rel, title, category, source, mtime, library, text):
        self._ctx.db.execute(
            "INSERT INTO kb_articles (relpath,title,category,source,mtime,library)"
            " VALUES (?,?,?,?,?,?) ON CONFLICT(relpath) DO UPDATE SET"
            " title=excluded.title, category=excluded.category, source=excluded.source,"
            " mtime=excluded.mtime, library=excluded.library",
            (rel, title, category, source, mtime, library))
        self._ctx.db.execute("DELETE FROM kb_fts WHERE relpath=?", (rel,))
        body = _tokenize_zh(re.sub(r"^---.*?---", "", text, flags=re.S)[:60000])
        self._ctx.db.execute(
            "INSERT INTO kb_fts (relpath, title, body) VALUES (?,?,?)",
            (rel, _tokenize_zh(title), body))

    @staticmethod
    def _parse_fm(text):
        m = re.match(r"^---\s*\n(.*?)\n---", text, flags=re.S)
        meta = {}
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"')
        return meta

    def count(self, library=None):
        if library:
            return self._ctx.db.query_one(
                "SELECT COUNT(*) n FROM kb_articles WHERE library=?", (library,))["n"]
        return self._ctx.db.query_one("SELECT COUNT(*) n FROM kb_articles")["n"]

    def list_paths(self, library="bagu"):
        return [{"relpath": r["relpath"]} for r in self._ctx.db.query(
            "SELECT relpath FROM kb_articles WHERE library=? ORDER BY relpath", (library,))]

    def meta(self, relpath):
        return self._ctx.db.query_one("SELECT * FROM kb_articles WHERE relpath=?", (relpath,))

    # ---- 入库（粘贴/上传/URL） ----
    def ingest(self, library, title, content, source_url="", ext="md"):
        root = self.writable_root(library)
        prefix = "custom" if library == "bagu" else library
        slug = re.sub(r'[\\/:*?"<>|\s]+', '-', title)[:40] or "untitled"
        fname = f"{slug}.md"
        path = root / fname
        i = 1
        while path.exists():
            path = root / f"{slug}-{i}.md"
            i += 1
        fm = "---\ntitle: \"%s\"\ncategory: 自建\nsource: %s\n---\n\n" % (
            title.replace('"', ''), source_url or "手动添加")
        path.write_text(fm + content, encoding="utf-8")
        rel = f"{prefix}/{path.name}"
        self._upsert_article(rel, title, "自建", source_url, str(path.stat().st_mtime), library,
                             fm + content)
        self.rebuild_graph()
        self.chunks_refresh()
        return {"relpath": rel, "title": title}

    def ingest_file(self, library, filename, data: bytes):
        """上传文件：md/txt 直存；docx 标准库解析；pdf 可选依赖。"""
        ext = Path(filename).suffix.lower()
        if ext in (".md", ".txt", ".markdown"):
            text = data.decode("utf-8", "ignore")
        elif ext == ".docx":
            text = _docx_to_text(data)
        elif ext == ".pdf":
            text = _pdf_to_text(data)
            if text is None:
                # 未装 pypdf：降级为占位（标题可搜，正文不可）
                title = Path(filename).stem
                return self.ingest(library, title,
                                   f"> [!提示] PDF 正文解析需要可选组件 pypdf（pip install pypdf），"
                                   f"安装后重新上传即可全文检索。")
        else:
            return {"error": f"暂不支持 {ext}（支持 md/txt/docx/pdf）"}
        title = Path(filename).stem
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, flags=re.S)
        if m and "title:" in m.group(1):
            t = re.search(r'title:\s*"?([^"\n]+)"?', m.group(1))
            if t:
                title = t.group(1).strip()
            text = m.group(2)
        return self.ingest(library, title, text, source_url=f"upload:{filename}")

    def ingest_url(self, library, url):
        """抓取网页正文转 Markdown（简单正文抽取：去 script/style/nav，保留标题与文本块）。"""
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 StudyWorkbench/0.2"})
        with urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", "ignore")
        tm = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
        title = (tm.group(1).strip() if tm else url)[:60]
        html = re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
        html = re.sub(r'</(p|div|h[1-6]|li)>', '\n', html, flags=re.I)
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()[:20000]
        return self.ingest(library, title or "网页存档", text, source_url=url)

    _WRITABLE_PREFIXES = ("custom/", "mianjing/", "grad/")

    def delete_article(self, relpath):
        """v1.19：删除可写库文章（custom/mianjing/grad）——磁盘文件 + 六表级联 + 相关边。
        bagu 库外只读挂载拒删（版权原因）。不存在返回 None。"""
        meta = self.meta(relpath)
        if not meta:
            return None
        if not relpath.startswith(self._WRITABLE_PREFIXES):
            raise ValueError("该文章在只读库（库外挂载），不可删除")
        f = self._resolve(meta["library"], relpath)
        if f and f.is_file():
            f.unlink()
        chunk_ids = [r["id"] for r in self._ctx.db.query(
            "SELECT id FROM kb_chunks WHERE relpath=?", (relpath,))]
        for cid in chunk_ids:
            self._ctx.db.execute("DELETE FROM kb_chunks_fts WHERE chunk_id=?", (cid,))
            self._ctx.db.execute("DELETE FROM kb_chunk_vec WHERE chunk_id=?", (cid,))
        for t in ("kb_chunks", "kb_articles", "kb_fts", "kb_chunks_meta"):
            self._ctx.db.execute(f"DELETE FROM {t} WHERE relpath=?", (relpath,))
        self._ctx.db.execute(
            "DELETE FROM kb_edges WHERE src=? OR dst=?", (relpath, relpath))
        self.rebuild_graph()
        self.chunks_refresh()
        return {"ok": True}

    # ---- 检索 / 阅读 / 双链 ----
    def search(self, q, limit=12, library=None):
        conds, params = ["kb_fts MATCH ?"], [_tokenize_zh(q.strip())]
        if library:
            conds.append("a.library = ?")
            params.append(library)
        params.append(limit)
        return self._ctx.db.query(
            "SELECT a.relpath, a.title, a.category, a.library,"
            " snippet(kb_fts, 2, '【', '】', '…', 12) AS hit"
            " FROM kb_fts f JOIN kb_articles a ON a.relpath=f.relpath"
            " WHERE " + " AND ".join(conds) + " LIMIT ?", tuple(params))

    def article(self, relpath):
        meta = self.meta(relpath)
        if not meta:
            return None
        f = self._resolve(meta["library"], relpath)
        if not f or not f.is_file():
            return None
        text = f.read_text(encoding="utf-8", errors="ignore")
        body = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
        wikilinks = _WIKILINK.findall(body)
        return {**meta, "body": body, "wikilinks": wikilinks,
                "backlinks": self.backlinks(relpath)}

    def backlinks(self, relpath):
        """引用本篇的文章（正文含 [[本篇标题]]，按标题短语匹配）。"""
        row = self.meta(relpath)
        if not row:
            return []
        pat = '"' + _tokenize_zh(row["title"]).strip() + '"'
        rows = self._ctx.db.query(
            "SELECT a.relpath, a.title, a.library FROM kb_fts f"
            " JOIN kb_articles a ON a.relpath=f.relpath WHERE kb_fts MATCH ? LIMIT 20", (pat,))
        return [r for r in rows if r["relpath"] != relpath]

    def tree(self, library="bagu"):
        """目录树导航 + 最近更新。"""
        arts = self._ctx.db.query(
            "SELECT relpath, title, category FROM kb_articles WHERE library=? ORDER BY relpath",
            (library,))
        return arts

    def ask(self, q, library=None):
        """问答主路径（F21 混合检索）：分块检索 → 上下文组装 → AI 生成；无 AI 降级参考回答。"""
        chunks = self.rag_retrieve(q, library=library, k=6)
        parts = []
        for c in chunks:
            sec = f" · {c['heading']}" if c["heading"] else ""
            parts.append(f"《{c['title']}{sec}》：\n{c['text']}")
        context = "\n\n".join(parts)
        ai = self._ctx.ai.chat([
            {"role": "system", "content": "你是后端/大模型面试辅导助手。优先依据给定资料回答并注明参考文章标题，"
                                          "资料不足以完整回答时可结合你的可靠知识补充（标注'补充'）；"
                                          "完全无关才说不知道。用简洁中文回答。"},
            {"role": "user", "content": "问题：" + q + "\n\n相关资料：\n" + context},
        ], feature="知识问答")
        # sources 与旧格式兼容（relpath/title/category/hit）
        seen, sources = set(), []
        for c in chunks:
            if c["relpath"] in seen:
                continue
            seen.add(c["relpath"])
            sources.append({"relpath": c["relpath"], "title": c["title"],
                            "category": c["category"],
                            "hit": c["text"][:80]})
        if ai:
            return {"answer": ai.strip(), "sources": sources, "ai_used": True}
        ref = "（AI 未配置——以下是知识库中最相关的段落，供参考）\n\n" + "\n\n".join(
            f"**《{c['title']}{' · ' + c['heading'] if c['heading'] else ''}》**"
            f"（{c['category'] or '文章'}）：{c['text'][:120]}…" for c in chunks[:4]) \
            if chunks else "知识库中没有找到相关内容。"
        return {"answer": ref, "sources": sources, "ai_used": False}

    # ================= RAG：分块 / 语义索引 / 混合检索（DESIGN F21/F22） =================

    def chunks_refresh(self):
        """增量分块入口：语料指纹未变跳过；变化文章重切（未变块的向量保留）。"""
        info = self._ctx.db.query_one(
            "SELECT COUNT(*) n, MAX(mtime) m FROM kb_articles")
        fp = f"{info['n']}:{info['m'] or ''}"
        self._ctx.db.execute(
            "CREATE TABLE IF NOT EXISTS kb_meta (k TEXT PRIMARY KEY, v TEXT)")
        stored = self._ctx.db.query_one("SELECT v FROM kb_meta WHERE k='rag_fp'")
        if stored and stored["v"] == fp:
            return 0
        arts = self._ctx.db.query("SELECT relpath, title FROM kb_articles")
        return self._chunks_rebuild_all(arts, fp)

    def _chunks_rebuild_all(self, arts, fp):
        """逐篇比对重建（chunks_refresh 的实际执行体，保留未变块的向量）。"""
        self._ctx.db.execute(
            "CREATE TABLE IF NOT EXISTS kb_chunks_meta (relpath TEXT PRIMARY KEY, chunks_md5 TEXT)")
        n = 0
        for a in arts:
            meta = self.meta(a["relpath"])
            f = self._resolve(meta["library"], a["relpath"]) if meta else None
            body = f.read_text(encoding="utf-8", errors="ignore") if f and f.is_file() else ""
            chs = kb_rag.chunk_article(a["title"], body)
            digest = hashlib.md5("\n§\n".join(
                f"{c['heading']}|{c['text']}" for c in chs).encode()).hexdigest()
            old = self._ctx.db.query_one(
                "SELECT chunks_md5 FROM kb_chunks_meta WHERE relpath=?", (a["relpath"],))
            if old and old["chunks_md5"] == digest:
                continue
            ids = [r["id"] for r in self._ctx.db.query(
                "SELECT id FROM kb_chunks WHERE relpath=?", (a["relpath"],))]
            for cid in ids:
                self._ctx.db.execute("DELETE FROM kb_chunks WHERE id=?", (cid,))
                self._ctx.db.execute("DELETE FROM kb_chunks_fts WHERE chunk_id=?", (cid,))
                self._ctx.db.execute("DELETE FROM kb_chunk_vec WHERE chunk_id=?", (cid,))
            for c in chs:
                cid = self._ctx.db.execute(
                    "INSERT INTO kb_chunks (relpath, seq, title, heading, text)"
                    " VALUES (?,?,?,?,?)",
                    (a["relpath"], c["seq"], a["title"], c["heading"], c["text"]))
                self._ctx.db.execute(
                    "INSERT INTO kb_chunks_fts (chunk_id, text) VALUES (?,?)",
                    (cid, _tokenize_zh(kb_rag.embed_text(a["title"], c["heading"], c["text"]))))
            self._ctx.db.execute(
                "INSERT INTO kb_chunks_meta (relpath, chunks_md5) VALUES (?,?)"
                " ON CONFLICT(relpath) DO UPDATE SET chunks_md5=excluded.chunks_md5",
                (a["relpath"], digest))
            n += 1
        self._ctx.db.execute(
            "INSERT INTO kb_meta (k, v) VALUES ('rag_fp', ?)"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (fp,))
        return n

    def rag_status(self):
        chunks = self._ctx.db.query_one("SELECT COUNT(*) n FROM kb_chunks")["n"]
        model = self._ctx.ai.embedding_model()
        embedded = self._ctx.db.query_one(
            "SELECT COUNT(*) n FROM kb_chunk_vec WHERE model=?", (model,))["n"]
        return {**self._rag_progress, "chunks": chunks, "embedded": embedded,
                "model": model, "ai_ready": self._ctx.ai.status()["configured"]}

    def rag_build(self):
        """一键构建（F22）：分块增量（本地）→ 后台批量嵌入缺失块；线程执行，进度见 rag_status。"""
        if self._rag_progress.get("building"):
            return {"started": False, "error": "正在构建中"}
        self._rag_progress = {"building": True, "done": 0, "total": 0,
                              "error": None, "started_at": now()}
        t = threading.Thread(target=self._rag_build_worker, daemon=True)
        t.start()
        return {"started": True}

    def _rag_build_worker(self):
        try:
            self.chunks_refresh()
            model = self._ctx.ai.embedding_model()
            todo = [r["id"] for r in self._ctx.db.query(
                "SELECT c.id FROM kb_chunks c LEFT JOIN kb_chunk_vec v"
                " ON v.chunk_id=c.id AND v.model=? WHERE v.chunk_id IS NULL", (model,))]
            self._rag_progress["total"] = len(todo)
            self._rag_progress["done"] = 0
            if not todo:
                return
            texts = {r["id"]: kb_rag.embed_text(r["title"], r["heading"], r["text"])
                     for r in self._ctx.db.query(
                         "SELECT id, title, heading, text FROM kb_chunks WHERE id IN"
                         f" ({','.join('?' * len(todo))})", todo)}
            ids = list(texts)
            STEP = 10
            for i in range(0, len(ids), STEP):
                batch_ids = ids[i:i + STEP]
                vecs = self._ctx.ai.embed([texts[cid] for cid in batch_ids])
                if vecs is None:
                    self._rag_progress["error"] = \
                        "embedding 调用失败（网络/额度），已暂停；再点一次『构建』会从断点继续"
                    return
                for cid, v in zip(batch_ids, vecs):
                    nv = kb_rag.l2_normalize(v)
                    self._ctx.db.execute(
                        "INSERT OR REPLACE INTO kb_chunk_vec (chunk_id, model, dim, vec)"
                        " VALUES (?,?,?,?)",
                        (cid, model, len(nv), kb_rag.vec_to_blob(nv)))
                self._rag_progress["done"] = min(i + STEP, len(ids))
        except Exception as e:  # 构建线程兜底：不崩溃服务
            self._rag_progress["error"] = str(e)
        finally:
            self._rag_progress["building"] = False

    def rag_retrieve(self, query, library=None, k=6, lexical_n=40):
        """混合检索（F21）：BM25 分块召回 → 语义重排 → 每篇≤2块、预算6000字。"""
        conds, params = ["kb_chunks_fts MATCH ?"], [_tokenize_zh(query)]
        join_lib = ""
        if library:
            conds.append("a.library = ?")
            params.append(library)
            join_lib = " JOIN kb_articles a ON a.relpath=c.relpath"
        else:
            join_lib = " JOIN kb_articles a ON a.relpath=c.relpath"
        params.append(lexical_n)
        rows = self._ctx.db.query(
            "SELECT c.id, c.relpath, c.title, c.heading, c.text, a.category, a.library"
            f" FROM kb_chunks_fts f JOIN kb_chunks c ON c.id=f.chunk_id{join_lib}"
            " WHERE " + " AND ".join(conds) + " ORDER BY rank LIMIT ?", tuple(params))
        if not rows:   # 关键词未命中：退回标题子串匹配
            kw = query.strip()
            rows = self._ctx.db.query(
                "SELECT c.id, c.relpath, c.title, c.heading, c.text, a.category, a.library"
                " FROM kb_chunks c JOIN kb_articles a ON a.relpath=c.relpath"
                " WHERE (?='' OR a.title LIKE '%'||?||'%')" +
                (" AND a.library=?" if library else "") +
                " ORDER BY c.relpath, c.seq LIMIT 20", ((library and ("", "", library)) or ("", "")))
        # 语义重排（混合得分 = 0.65×cos + 0.35×位置分）
        qvec = None
        if rows and self._ctx.ai.status()["configured"]:
            emb = self._ctx.ai.embed([query])
            if emb:
                qvec = kb_rag.l2_normalize(emb[0])
        scored = []
        for pos, r in enumerate(rows):
            lex = 1.0 - pos / max(1, len(rows))
            cos = 0.0
            if qvec is not None:
                vrow = self._ctx.db.query_one(
                    "SELECT vec FROM kb_chunk_vec WHERE chunk_id=? AND model=?",
                    (r["id"], self._ctx.ai.embedding_model()))
                if vrow:
                    cos = kb_rag.cosine(qvec, kb_rag.blob_to_vec(vrow["vec"]))
            scored.append({**r, "score": round(0.65 * cos + 0.35 * lex, 4) if qvec is not None
                           else round(lex, 4), "semantic": qvec is not None})
        scored.sort(key=lambda x: -x["score"])
        out, per_art, budget = [], Counter(), 6000
        for c in scored:
            if per_art[c["relpath"]] >= 2 or budget - len(c["text"]) < 0 or len(out) >= k:
                continue
            per_art[c["relpath"]] += 1
            budget -= len(c["text"])
            out.append({key: c[key] for key in
                        ("relpath", "title", "heading", "text", "category", "score")})
        return out

    # ---- 图谱（F16） ----
    def rebuild_graph(self):
        """全量重建 auto（关键词共现）与 wikilink 边；manual 边与黑名单叠加。
        指纹缓存：文章数/mtime/边数没变则跳过（避免每次启动重算 20 秒布局）。"""
        info = self._ctx.db.query_one(
            "SELECT COUNT(*) n, MAX(mtime) m FROM kb_articles")
        edge_n = self._ctx.db.query_one("SELECT COUNT(*) n FROM kb_edges")["n"]
        fp = f"{info['n']}:{info['m'] or ''}:{edge_n}"
        self._ctx.db.execute(
            "CREATE TABLE IF NOT EXISTS kb_meta (k TEXT PRIMARY KEY, v TEXT)")
        stored = self._ctx.db.query_one(
            "SELECT v FROM kb_meta WHERE k='graph_fp'")
        if stored and stored["v"] == fp:
            return
        arts = self._ctx.db.query(
            "SELECT relpath, title, category, library FROM kb_articles")
        kw = {}
        for a in arts:
            f = self._resolve(a["library"], a["relpath"])
            body = ""
            if f and f.is_file():
                body = f.read_text(encoding="utf-8", errors="ignore")[:8000]
            kw[a["relpath"]] = _extract_keywords(a["title"], body) | {a["title"]}
        self._ctx.db.execute("DELETE FROM kb_edges WHERE type IN ('auto','wikilink')")
        rels = {a["relpath"]: a for a in arts}
        keys = list(kw)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                common = kw[keys[i]] & kw[keys[j]]
                if len(common) >= 3 or (len(common) >= 2 and
                                        rels[keys[i]]["title"] in kw[keys[j]]):
                    self._ctx.db.execute(
                        "INSERT OR IGNORE INTO kb_edges (src,dst,type,weight) VALUES (?,?,?,?)",
                        (keys[i], keys[j], "auto", len(common)))
        # wikilink 边
        for a in arts:
            f = self._resolve(a["library"], a["relpath"])
            if not f or not f.is_file():
                continue
            for link in _WIKILINK.findall(f.read_text(encoding="utf-8", errors="ignore")):
                for b in arts:
                    if b["relpath"] != a["relpath"] and (link == b["title"] or link in b["title"]):
                        s, d = sorted([a["relpath"], b["relpath"]])
                        self._ctx.db.execute(
                            "INSERT OR IGNORE INTO kb_edges (src,dst,type,weight) VALUES (?,?,?,?)",
                            (s, d, "wikilink", 3))
        # 删除黑名单 auto 边
        self._ctx.db.execute(
            "DELETE FROM kb_edges WHERE type='auto' AND (src,dst) IN"
            " (SELECT src,dst FROM kb_edge_blacklist)")
        # 确定性布局：服务端离线计算并缓存坐标（前端零力模拟）
        self._compute_layout(arts)
        # 写指纹（用重建后的边数）
        edge_n2 = self._ctx.db.query_one("SELECT COUNT(*) n FROM kb_edges")["n"]
        self._ctx.db.execute(
            "INSERT INTO kb_meta (k, v) VALUES ('graph_fp', ?)"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v",
            (f"{info['n']}:{info['m'] or ''}:{edge_n2}",))

    def _compute_layout(self, arts, rounds=160):
        """简化力导向（类目锚点圆环 + 斥力 + 弹簧），结果缓存 kb_layout。"""
        import math, random
        self._ctx.db.execute(
            "CREATE TABLE IF NOT EXISTS kb_layout (relpath TEXT PRIMARY KEY, x REAL, y REAL)")
        random.seed(42)  # 确定性
        cats = sorted({a["category"] or "其他" for a in arts})
        anchors = {}
        for i, c in enumerate(cats):
            ang = 2 * math.pi * i / max(1, len(cats))
            anchors[c] = (500 + math.cos(ang) * 320, 400 + math.sin(ang) * 280)
        pos = {}
        for a in arts:
            ax, ay = anchors.get(a["category"] or "其他", (500, 400))
            pos[a["relpath"]] = [ax + random.uniform(-70, 70), ay + random.uniform(-70, 70)]
        keys = list(pos)
        edges = self._ctx.db.query(
            "SELECT src, dst, weight FROM kb_edges WHERE type != 'manual'")
        for _ in range(rounds):
            alpha = max(0.05, 1 - _ / rounds)
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    ax_, ay_ = pos[keys[i]]; bx_, by_ = pos[keys[j]]
                    dx, dy = ax_ - bx_, ay_ - by_
                    d2 = dx * dx + dy * dy
                    if d2 < 1 or d2 > 60000:
                        continue
                    d = math.sqrt(d2)
                    f = 6000 / d2 * alpha
                    fx, fy = dx / d * f, dy / d * f
                    pos[keys[i]][0] += fx; pos[keys[i]][1] += fy
                    pos[keys[j]][0] -= fx; pos[keys[j]][1] -= fy
            for e in edges:
                a, b = pos.get(e["src"]), pos.get(e["dst"])
                if not a or not b:
                    continue
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.sqrt(dx * dx + dy * dy) or 1
                f = (d - 90) * 0.02 * alpha
                a[0] += dx / d * f; a[1] += dy / d * f
                b[0] -= dx / d * f; b[1] -= dy / d * f
            for a in arts:
                p = pos[a["relpath"]]
                ax_, ay_ = anchors.get(a["category"] or "其他", (500, 400))
                p[0] += (ax_ - p[0]) * 0.02 * alpha + (500 - p[0]) * 0.004
                p[1] += (ay_ - p[1]) * 0.02 * alpha + (400 - p[1]) * 0.004
        for rel, (x, y) in pos.items():
            self._ctx.db.execute(
                "INSERT INTO kb_layout (relpath, x, y) VALUES (?,?,?)"
                " ON CONFLICT(relpath) DO UPDATE SET x=excluded.x, y=excluded.y", (rel, x, y))

    def graph(self, library="bagu"):
        arts = self._ctx.db.query(
            "SELECT a.relpath, a.title, a.category, l.x, l.y FROM kb_articles a"
            " LEFT JOIN kb_layout l ON l.relpath = a.relpath WHERE a.library=?", (library,))
        ids = {a["relpath"] for a in arts}
        edges = self._ctx.db.query(
            "SELECT * FROM kb_edges WHERE src IN (SELECT relpath FROM kb_articles WHERE library=?)"
            " AND dst IN (SELECT relpath FROM kb_articles WHERE library=?)", (library, library))
        deg = Counter()
        for e in edges:
            deg[e["src"]] += 1
            deg[e["dst"]] += 1
        return {
            "nodes": [{"id": a["relpath"], "title": a["title"], "category": a["category"],
                       "degree": deg[a["relpath"]], "x": a["x"] or 500, "y": a["y"] or 400}
                      for a in arts],
            "edges": [{"src": e["src"], "dst": e["dst"], "type": e["type"],
                       "weight": e["weight"]} for e in edges if e["src"] in ids and e["dst"] in ids],
        }

    def add_manual_edge(self, src, dst):
        s, d = sorted([src, dst])
        self._ctx.db.execute("DELETE FROM kb_edge_blacklist WHERE src=? AND dst=?", (s, d))
        self._ctx.db.execute(
            "INSERT OR IGNORE INTO kb_edges (src,dst,type,weight) VALUES (?,?,?,?)",
            (s, d, "manual", 2))
        return {"ok": True}

    def remove_edge(self, src, dst):
        s, d = sorted([src, dst])
        self._ctx.db.execute("DELETE FROM kb_edges WHERE src=? AND dst=?", (s, d))
        self._ctx.db.execute(
            "INSERT OR IGNORE INTO kb_edge_blacklist (src,dst) VALUES (?,?)", (s, d))
        return {"ok": True}

    # ---- 收藏（保留） ----
    def add_clip(self, title, content="", link="", tags=""):
        cid = self._ctx.db.execute(
            "INSERT INTO kb_clips (title, content, link, tags, created_at) VALUES (?,?,?,?,?)",
            (title, content, link, tags, now()))
        return cid

    def clips(self, limit=100):
        return self._ctx.db.query("SELECT * FROM kb_clips ORDER BY id DESC LIMIT ?", (limit,))

    def delete_clip(self, cid):
        self._ctx.db.execute("DELETE FROM kb_clips WHERE id=?", (cid,))


def register(ctx: AppContext):
    ctx.services.register(KbService.name, KbService(ctx))


def post_migrate(ctx: AppContext):
    svc = ctx.services.get(KbService.name)
    svc.scan()
