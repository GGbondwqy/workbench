# -*- coding: utf-8 -*-
"""雅思域（DESIGN v2.0/v2.1）：刷题题库与作答 / 真题分数趋势 / 错题题型统计 /
口语话题库 / 写作积累 / 模考与考试日设置。

设置（考试日/目标分/模考周期）存 settings 域（页内常驻可改），本域只管记录与统计。
刷题题库（F17/F18）：内置原创仿真题 + 本机 data/ielts_bank/*.json（公开收集/手工导入），
第三方内容不进仓库（版权边界同八股文库）。
"""
import json
import re
from datetime import datetime
from pathlib import Path

from app.core.registry import AppContext
from app.core.timeutil import today

MIGRATIONS = [
    ("0017_ielts", """
        CREATE TABLE IF NOT EXISTS ielts_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            book TEXT DEFAULT '',            -- 剑18
            test_no TEXT DEFAULT '',
            listening REAL, reading REAL,
            writing REAL, speaking REAL,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ielts_mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            subject TEXT NOT NULL,           -- listening/reading
            qtype TEXT NOT NULL,             -- Heading/配对/填空…
            reason TEXT DEFAULT '',
            ref TEXT DEFAULT ''              -- 剑18-T2-P1-Q14
        );
        CREATE TABLE IF NOT EXISTS ielts_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part INTEGER DEFAULT 2,
            topic TEXT NOT NULL,
            freq INTEGER DEFAULT 0,          -- 高频标记
            practiced INTEGER DEFAULT 0,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ielts_writings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            topic TEXT NOT NULL,
            content TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ielts_mocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            kind TEXT DEFAULT 'full',        -- full/listening/reading…
            note TEXT DEFAULT ''
        );
    """),
    ("0020_ielts_bank", """
        CREATE TABLE IF NOT EXISTS ielts_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            date TEXT NOT NULL,
            total INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            detail TEXT DEFAULT '[]'         -- JSON: 逐题结果
        );
    """),
    # v1.15 口语升级：seed 话题挂 seed_id；"我的版本"存 ielts_speak_notes
    ("0023_ielts_speak", """
        ALTER TABLE ielts_topics ADD COLUMN seed_id TEXT DEFAULT '';
        CREATE TABLE IF NOT EXISTS ielts_speak_notes (
            seed_id TEXT PRIMARY KEY,
            text TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        );
    """),
    # v1.16 写作："我的作文"存 ielts_write_notes
    ("0024_ielts_write", """
        CREATE TABLE IF NOT EXISTS ielts_write_notes (
            seed_id TEXT PRIMARY KEY,
            text TEXT DEFAULT '',
            updated_at TEXT NOT NULL
        );
    """),
]

SUBJECT_CN = {"listening": "听力", "reading": "阅读", "writing": "写作", "speaking": "口语"}
TYPE_CN = {"choice": "单选", "tfng": "判断", "blank": "填空"}


class IeltsService:
    name = "ielts_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx
        from app.core.timeutil import now
        self._now = now

    # ---- 设置（考试日/目标分，存 settings 域） ----
    def config(self):
        default = {"exam_date": None, "target_overall": 7.0,
                   "target": {"listening": 7.0, "reading": 7.5, "writing": 6.5, "speaking": 6.5}}
        cfg = self._ctx.services.get("settings_service").get("ielts")
        if isinstance(cfg, dict):
            default.update(cfg)
        return default

    def set_config(self, patch: dict):
        cfg = self.config()
        cfg.update(patch)
        self._ctx.services.get("settings_service").set("ielts", cfg)
        return cfg

    def days_left(self):
        d = self.config().get("exam_date")
        if not d:
            return None
        try:
            return (datetime.strptime(d, "%Y-%m-%d").date() -
                    datetime.strptime(today(), "%Y-%m-%d").date()).days
        except ValueError:
            return None

    # ---- 真题记录 ----
    def add_test(self, day, book, test_no, listening=None, reading=None,
                 writing=None, speaking=None, note=""):
        tid = self._ctx.db.execute(
            "INSERT INTO ielts_tests (date, book, test_no, listening, reading, writing,"
            " speaking, note) VALUES (?,?,?,?,?,?,?,?)",
            (day, book, test_no, listening, reading, writing, speaking, note))
        return tid

    def tests(self):
        return self._ctx.db.query("SELECT * FROM ielts_tests ORDER BY date, id")

    def trend(self):
        """四科分数序列（供前端画趋势）。"""
        rows = self.tests()
        out = {"dates": [], "listening": [], "reading": [], "writing": [], "speaking": []}
        for r in rows:
            out["dates"].append(f"{r['book']} {r['test_no']}".strip() or r["date"])
            for k in ("listening", "reading", "writing", "speaking"):
                out[k].append(r[k])
        return out

    # ---- 错题本 ----
    def add_mistake(self, day, subject, qtype, reason="", ref=""):
        mid = self._ctx.db.execute(
            "INSERT INTO ielts_mistakes (date, subject, qtype, reason, ref) VALUES (?,?,?,?,?)",
            (day, subject, qtype, reason, ref))
        return mid

    def mistakes(self, limit=200):
        return self._ctx.db.query(
            "SELECT * FROM ielts_mistakes ORDER BY date DESC LIMIT ?", (limit,))

    def mistake_stats(self):
        return self._ctx.db.query(
            "SELECT subject, qtype, COUNT(*) n FROM ielts_mistakes"
            " GROUP BY subject, qtype ORDER BY n DESC")

    def delete_mistake(self, mid):
        """v1.19：错题本删除。"""
        self._ctx.db.execute("DELETE FROM ielts_mistakes WHERE id=?", (mid,))

    def delete_bank_set(self, set_id):
        """v1.19：删除本机题库文件题组（data/ielts_bank/*.json，如新闻出题）。
        内置 seed（代码内置无文件）拒删。该题组作答留痕与错题一并清理。"""
        s = self.bank_get(set_id)
        if not s:
            raise ValueError("题组不存在")
        p = self._bank_dir() / f"{set_id}.json"
        if not p.is_file():
            raise ValueError("内置题组不可删除（只有新闻出题/导入的本机题组可删）")
        p.unlink()
        self._ctx.db.execute("DELETE FROM ielts_attempts WHERE set_id=?", (set_id,))
        # 错题 ref 形如 "{题组标题} Q{题号}"（bank_submit 写入口径）
        self._ctx.db.execute("DELETE FROM ielts_mistakes WHERE ref LIKE ?",
                             (f"{s['title']} Q%",))
        return {"ok": True}

    # ---- 口语话题 ----
    def add_topic(self, part, topic, freq=0):
        tid = self._ctx.db.execute(
            "INSERT INTO ielts_topics (part, topic, freq) VALUES (?,?,?)", (part, topic, freq))
        return tid

    def topics(self):
        """高频未练排前。"""
        return self._ctx.db.query(
            "SELECT * FROM ielts_topics ORDER BY practiced ASC, freq DESC, id")

    def toggle_practiced(self, tid):
        self._ctx.db.execute(
            "UPDATE ielts_topics SET practiced = 1 - practiced WHERE id=?", (tid,))

    def delete_topic(self, tid):
        self._ctx.db.execute("DELETE FROM ielts_topics WHERE id=?", (tid,))

    # ---- 写作积累 ----
    def add_writing(self, day, topic, content=""):
        wid = self._ctx.db.execute(
            "INSERT INTO ielts_writings (date, topic, content) VALUES (?,?,?)",
            (day, topic, content))
        return wid

    def writings(self, limit=100):
        return self._ctx.db.query(
            "SELECT * FROM ielts_writings ORDER BY id DESC LIMIT ?", (limit,))

    # ---- 模考 ----
    def add_mock(self, day, kind="full", note=""):
        mid = self._ctx.db.execute(
            "INSERT INTO ielts_mocks (date, kind, note) VALUES (?,?,?)", (day, kind, note))
        return mid

    def mocks(self):
        return self._ctx.db.query(
            "SELECT * FROM ielts_mocks WHERE date >= ? ORDER BY date", (today(),))

    def delete_mock(self, mid):
        self._ctx.db.execute("DELETE FROM ielts_mocks WHERE id=?", (mid,))

    def upcoming_mocks(self, days=7):
        out = []
        for m in self.mocks():
            try:
                left = (datetime.strptime(m["date"], "%Y-%m-%d").date() -
                        datetime.strptime(today(), "%Y-%m-%d").date()).days
                if 0 <= left <= days:
                    out.append({"date": m["date"], "kind": m["kind"], "days_left": left})
            except ValueError:
                continue
        return out

    # ================= 刷题题库（F17/F18，v2.1） =================

    def _bank_dir(self) -> Path:
        p = self._ctx.data_dir / "ielts_bank"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _bank_sets(self):
        """内置仿真题 + 本机题库文件夹（data/ielts_bank/*.json）。坏文件跳过。"""
        from app.services.ielts_seed import SEED_SETS
        sets = [dict(s) for s in SEED_SETS]
        for f in sorted(self._bank_dir().glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            items = data if isinstance(data, list) else [data]
            for s in items:
                if self._validate_set(s, strict=False):
                    s = dict(s)
                    s.setdefault("id", f.stem)
                    s.setdefault("source", "public")
                    sets.append(s)
        return sets

    @staticmethod
    def _validate_set(s, strict=True):
        ok = (isinstance(s, dict) and s.get("subject") in ("listening", "reading")
              and isinstance(s.get("title"), str) and s.get("title")
              and isinstance(s.get("sections"), list) and s["sections"])
        if not ok:
            return False
        for sec in s["sections"]:
            if not isinstance(sec, dict) or not isinstance(sec.get("questions"), list):
                return False
            for q in sec["questions"]:
                if not isinstance(q, dict) or not q.get("no") or \
                        q.get("type") not in ("choice", "tfng", "blank") or \
                        not str(q.get("answer", "")).strip():
                    return False
                if q["type"] == "choice" and not isinstance(q.get("options"), list):
                    return False
        return True

    def bank_list(self, subject=None):
        out = []
        for s in self._bank_sets():
            if subject and s["subject"] != subject:
                continue
            n = sum(len(sec["questions"]) for sec in s["sections"])
            best = self._ctx.db.query_one(
                "SELECT MAX(CAST(correct AS FLOAT)/MAX(total,1)) m FROM ielts_attempts"
                " WHERE set_id=?", (s["id"],))["m"]
            out.append({"id": s["id"], "subject": s["subject"], "title": s["title"],
                        "source": s.get("source", "public"), "n_questions": n,
                        "best": round(best * 100) if best is not None else None})
        return out

    def bank_get(self, set_id):
        for s in self._bank_sets():
            if s["id"] == set_id:
                return s
        return None

    # ================= 新闻出题（v1.14，纯脚本零 AI 依赖） =================
    # 原文/音频只落本机 data/（版权红线同题库）；源实测可达性见 PHASE_LOG v1.14。
    _UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    _STOPWORDS = set("""about above after again against being below between during
        further having their there these those through under until before because
        without within should could would really think thing things going want
        people something anything everything nothing maybe quite rather perhaps
        little might must shall doesn don wasn didn isn aren won couldn shouldn
        yourself whether around another always never often usually sometimes
        question questions speaker listeners programme program episode minutes""".split())

    # ---- 通用解析纯函数（离线可测） ----
    @classmethod
    def _http_get(cls, url, timeout=15, limit=300000):
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": cls._UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(limit).decode("utf-8", "replace")

    @staticmethod
    def _strip_html(html):
        """去 script/style 与标签 → 非空文本行列表（≥25 字符）。"""
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
        html = re.sub(r"<[^>]+>", "\n", html)
        for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'),
                     ("&#39;", "'"), ("&apos;", "'"), ("&ndash;", "-"), ("&mdash;", "—"),
                     ("&rsquo;", "'"), ("&lsquo;", "'"), ("&ldquo;", '"'), ("&rdquo;", '"')):
            html = html.replace(a, b)
        return [l.strip() for l in html.split("\n") if len(l.strip()) >= 25]

    @staticmethod
    def _slugify(text, maxlen=40):
        s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
        return (s[:maxlen].rstrip("-") or "untitled")

    @staticmethod
    def _extract_title(html):
        m = re.search(r'property="og:title" content="([^"]+)"', html) \
            or re.search(r"<title>([^<]+)</title>", html)
        if not m:
            return "Untitled"
        t = (m.group(1).replace("&amp;", "&").replace("&#39;", "'")
             .replace("&apos;", "'").replace("&quot;", '"')
             .replace("&rsquo;", "'").replace("&lsquo;", "'")
             .replace("&ldquo;", '"').replace("&rdquo;", '"').strip())
        # BBC LE 标题常带站名后缀
        return re.sub(r"\s*[-|]\s*(BBC|VOA|Learning English).*$", "", t).strip() or "Untitled"

    # ---- 各源解析（纯函数：html → [{url, id}] / 详情 dict） ----
    @classmethod
    def _parse_bbc_le_list(cls, html):
        """6 Minute English 列表页 → 最新在前。"""
        items = re.findall(r'data-feature-item="(/features/6-minute-english_\d{4}/ep-\d+)"', html)
        out, seen = [], set()
        for path in items:
            eid = path.rsplit("/", 1)[-1]          # ep-261022
            if eid in seen:
                continue
            seen.add(eid)
            out.append({"url": "https://www.bbc.co.uk/learningenglish" + path, "id": eid})
        return out

    @classmethod
    def _parse_bbc_le_detail(cls, html):
        mp3 = re.findall(r'(https://downloads\.bbc\.co\.uk[^"\'\s<>]+?\.mp3)', html)
        marker = html.find("This is not a word-for-word")
        seg = html[marker:] if marker > 0 else html
        lines = cls._strip_html(seg[:40000])
        lines = [l for l in lines if "word-for-word" not in l
                 and not set(l) <= {"_", " ", "-"}]
        return {"mp3": mp3[0] if mp3 else None, "text": "\n".join(lines[:80])}

    @classmethod
    def _parse_bbc_news_list(cls, html):
        ids = list(dict.fromkeys(re.findall(r'/news/articles/(c[a-z0-9]+)', html)))
        return [{"url": "https://www.bbc.com/news/articles/" + i, "id": i} for i in ids]

    @classmethod
    def _parse_voa_list(cls, html):
        out, seen = [], set()
        for path, title in re.findall(r'href="(/a/(?:[a-z0-9-]+/)?\d{6,}\.html)"[^>]*>(.{5,150}?)<', html, re.S):
            title = re.sub(r"<[^>]+>", "", title).strip()
            base = path.split("/")[-1]
            if base in seen:
                continue
            # 排除固定课程页
            if any(k in path for k in ("lets-learn", "lets-teach", "teacher-tools",
                                       "english-in-a-minute", "news-words", "everyday-grammar")):
                continue
            seen.add(base)
            out.append({"url": "https://learningenglish.voanews.com" + path, "id": base})
        return out

    @classmethod
    def _parse_voa_detail(cls, html):
        mp3 = re.findall(r'(https://[^"\'\s<>]+?\.mp3)', html)
        paras = [re.sub(r"<[^>]+>", "", p).strip()
                 for p in re.findall(r"<p>([^<]{50,}?)</p>", html)]
        paras = [p for p in paras if not re.match(
            r"(?i)^(download|click|lesson plan|for Educators|Next up)", p)]
        return {"mp3": mp3[0] if mp3 else None, "text": "\n".join(paras[:30])}

    _NEWS_SOURCES = {
        "listening": [
            ("bbc", "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english",
             "_parse_bbc_le_list", "_parse_bbc_le_detail", "BBC Learning English"),
            ("voa", "https://learningenglish.voanews.com/",
             "_parse_voa_list", "_parse_voa_detail", "VOA Learning English"),
        ],
        "reading": [
            ("bbc", "https://www.bbc.com/news",
             "_parse_bbc_news_list", "_parse_bbc_news_detail", "BBC News"),
            ("voa", "https://learningenglish.voanews.com/",
             "_parse_voa_list", "_parse_voa_detail", "VOA Learning English"),
        ],
    }

    @classmethod
    def _parse_bbc_news_detail(cls, html):
        paras = re.findall(r"<p[^>]*>([^<]{50,}?)</p>", html)
        paras = [re.sub(r"<[^>]+>", "", p).strip() for p in paras]
        paras = [p for p in paras if not re.match(r"(?i)^(image |getty|afp|reuters)", p)]
        return {"mp3": None, "text": "\n".join(paras[:30])}

    # ---- 出题（纯函数） ----
    @classmethod
    def _gen_quiz(cls, text, n=8, rng=None):
        """程序出题：一半 blank（挖空填原词）+ 一半 choice（挖空句选词，干扰词取自词池）。"""
        rng = rng or __import__("random").Random()
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
                 if 40 <= len(s.strip()) <= 220]
        picks = []   # (sentence, word)
        seen_words = set()
        step = max(1, len(sents) // max(n, 4))
        for s in sents[::step]:
            words = re.findall(r"[A-Za-z]{6,}[a-z']*", s)
            words = [w.strip("'") for w in words]
            cands = [w for w in words if w.lower() not in cls._STOPWORDS
                     and w.lower() not in seen_words and not w.isupper()]
            if cands:
                w = rng.choice(cands[:6])
                picks.append((s, w))
                seen_words.add(w.lower())
            if len(picks) >= n:
                break
        if len(picks) < 4:
            return None
        picks = picks[:n]
        pool = [w for _, w in picks]
        questions = []
        for i, (s, w) in enumerate(picks):
            stem = s.replace(w, "______", 1)
            if rng.random() < 0.5 or len(pool) < 4:   # blank
                questions.append({"no": i + 1, "type": "blank",
                                  "stem": f"Fill the missing word: {stem}",
                                  "answer": w.lower(),
                                  "explain": f"原句：{s}"})
            else:                                     # choice
                distractors = [x for x in pool if x.lower() != w.lower()]
                rng.shuffle(distractors)
                opts = [w] + distractors[:3]
                rng.shuffle(opts)
                letters = "ABCD"
                questions.append({"no": i + 1, "type": "choice",
                                  "stem": f"Which word fills the gap? {stem}",
                                  "options": opts,
                                  "answer": letters[opts.index(w)],
                                  "explain": f"原句：{s}"})
        return questions

    # ---- 编排：抓取 → 出题 → 落库 ----
    def news_fetch(self, kind="reading", source="auto", count=1):
        """抓最新文章生成题组（纯脚本）。返回 {items, skipped, failed}。"""
        import random
        rng = random.Random()
        if kind not in ("listening", "reading"):
            return (400, {"error": "kind 须为 listening/reading"})
        count = min(max(int(count or 1), 1), 5)
        sources = self._NEWS_SOURCES[kind]
        if source != "auto":
            sources = [s for s in sources if s[0] == source]
            if not sources:
                return (400, {"error": f"source 须为 auto/{'/'.join(s[0] for s in self._NEWS_SOURCES[kind])}"})
        existing = {p.stem for p in self._bank_dir().glob("public-news-*")}
        items, skipped, failed = [], [], []
        for src_key, list_url, list_fn, detail_fn, src_name in sources:
            if len(items) >= count:
                break
            try:
                listing = getattr(self, list_fn)(self._http_get(list_url))
            except Exception as e:
                failed.append(f"{src_name} 列表不可达：{str(e)[:60]}")
                continue
            for cand in listing:
                if len(items) >= count:
                    break
                set_id = f"public-news-{src_key}-{cand['id']}"
                if set_id in existing:
                    skipped.append(cand["id"])
                    continue
                try:
                    html = self._http_get(cand["url"])
                    detail = getattr(self, detail_fn)(html)
                    title = self._extract_title(html)
                    qs = self._gen_quiz(detail["text"], rng=rng)
                    if not qs or len(detail["text"]) < 300:
                        skipped.append(cand["id"])
                        continue
                    day = datetime.strptime(today(), "%Y-%m-%d").strftime("%Y%m%d")
                    s = {"id": set_id, "subject": kind, "source": "public",
                         "title": f"新闻 · {title}（{src_name}）",
                         "note": (f"原文/音频出自 {src_name}（{cand['url']}）。"
                                  "题目为程序自动生成（挖空/选词），仅存本机学习使用。"),
                         "sections": [{"intro": "程序生成 · 挖空与选词混合",
                                       "material": detail["text"],
                                       "questions": qs}]}
                    p = self._bank_dir() / f"{set_id}.json"
                    p.write_text(json.dumps(s, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
                    # 真音频：下载到本机音频目录（慢连接保护：90s 总时长 + 30MB 上限；
                    # 失败不阻断 → TTS 兜底）
                    has_audio = False
                    if detail.get("mp3"):
                        try:
                            import time as _t
                            import urllib.request
                            req = urllib.request.Request(detail["mp3"],
                                                         headers={"User-Agent": self._UA})
                            data = bytearray()
                            t0 = _t.time()
                            with urllib.request.urlopen(req, timeout=20) as resp:
                                while len(data) < 30 * 1024 * 1024:
                                    chunk = resp.read(65536)
                                    if not chunk:
                                        break
                                    data.extend(chunk)
                                    if _t.time() - t0 > 90:
                                        raise TimeoutError("audio download too slow")
                            if len(data) > 300000:   # 小于 300KB 视为坏文件
                                (self._ctx.data_dir / "ielts_audio").mkdir(exist_ok=True)
                                (self._ctx.data_dir / "ielts_audio" / f"{set_id}.mp3") \
                                    .write_bytes(bytes(data))
                                has_audio = True
                        except Exception:
                            pass
                    existing.add(set_id)
                    items.append({"id": set_id, "title": s["title"],
                                  "n_questions": len(qs), "has_audio": has_audio})
                except Exception as e:
                    failed.append(f"{cand['id']}：{str(e)[:60]}")
        if not items and not skipped and failed:
            return (502, {"error": "；".join(failed)})
        return {"items": items, "skipped": skipped, "failed": failed}



    _AUDIO_EXTS = (".mp3", ".m4a", ".wav", ".ogg")

    def audio_file(self, set_id, sec):
        """本机音频查找（F26 双通道之一）：data/ielts_audio/{set_id}-{sec}.mp3 →
        {set_id}.mp3（整套共用一条音频）。找到返回 Path，否则 None（前端降级机器朗读）。"""
        sid = str(set_id or "")
        if not sid or "/" in sid or "\\" in sid or ".." in sid:
            return None
        base = self._ctx.data_dir / "ielts_audio"
        for cand in (f"{sid}-{sec}", sid):
            for ext in self._AUDIO_EXTS:
                p = base / (cand + ext)
                if p.is_file():
                    return p
        return None

    _TFNG = {"t": "T", "true": "T", "是": "T", "y": "T", "yes": "T", "对": "T",
             "f": "F", "false": "F", "否": "F", "n": "F", "no": "F", "错": "F",
             "ng": "NG", "notgiven": "NG", "not given": "NG", "ni": "NG", "未提及": "NG"}

    @classmethod
    def _normalize(cls, text):
        return re.sub(r"[\s\W_]+", "", str(text or "").lower(), flags=re.UNICODE) \
            .replace("，", "").replace("。", "")

    def _grade_one(self, q, user):
        """返回 (对错, 标准答案)。作答可为空（判错）；choice 支持字母或选项原文。"""
        ans = str(q["answer"]).strip()
        if user is None or not str(user).strip():
            return False, ans
        u = str(user).strip()
        if q["type"] == "tfng":
            key = self._TFNG.get(u.lower(), u)
            return key == ans.upper().replace(" ", ""), ans
        u_norm = self._normalize(u)
        if q["type"] == "blank":
            return any(u_norm == self._normalize(a) for a in ans.split("|")), ans
        # choice
        letters = "ABCDEFGHI"

        def letter_of(x):
            x = x.strip()
            return x[0].upper() if x and x[0].upper() in letters else None

        ans_letter, u_letter = letter_of(ans), letter_of(u)
        if ans_letter and u_letter and u_letter == ans_letter:
            return True, ans
        if u_norm == self._normalize(ans):
            return True, ans
        for i, o in enumerate(str(x) for x in (q.get("options") or [])):
            if u_norm and u_norm == self._normalize(o):
                if (ans_letter and letters[i] == ans_letter) or \
                        self._normalize(ans) in self._normalize(o):
                    return True, ans
        return False, ans

    def bank_submit(self, set_id, answers):
        """判分 + 错题自动入错题本 + 作答留痕（F17）。answers: {题号: 用户作答}"""
        s = self.bank_get(set_id)
        if not s:
            return None
        answers = answers or {}
        results, correct = [], 0
        for sec in s["sections"]:
            for q in sec["questions"]:
                user = answers.get(str(q["no"]))
                ok, std = self._grade_one(q, user)
                if ok:
                    correct += 1
                else:
                    self.add_mistake(
                        today(), s["subject"], TYPE_CN.get(q["type"], q["type"]),
                        f"你的答案：{user if str(user or '').strip() else '未作答'}；"
                        f"正确：{std}", f"{s['title']} Q{q['no']}")
                results.append({"no": q["no"], "type": q["type"],
                                "user": user if user is not None else "",
                                "answer": std, "correct": ok,
                                "explain": q.get("explain", "")})
        total = len(results)
        self._ctx.db.execute(
            "INSERT INTO ielts_attempts (set_id, subject, date, total, correct, detail)"
            " VALUES (?,?,?,?,?,?)",
            (set_id, s["subject"], today(), total, correct,
             json.dumps(results, ensure_ascii=False)))
        self._bump_goal(s["subject"])
        return {"set_id": set_id, "title": s["title"], "total": total,
                "correct": correct, "score": round(correct / total * 100) if total else 0,
                "results": results}

    def _bump_goal(self, subject):
        """刷题推进对应雅思里程碑（听力精听/阅读训练），goal 域未就绪则跳过。"""
        kw = "听力精听" if subject == "listening" else "阅读训练"
        try:
            row = self._ctx.db.query_one(
                "SELECT m.id FROM goal_milestones m JOIN goal_goals g"
                " ON m.goal_id=g.id WHERE m.title LIKE ? AND g.archived=0", (f"%{kw}%",))
            if row:
                self._ctx.services.get("goal_service").record_progress(row["id"])
        except Exception:
            pass

    def bank_import(self, body):
        """手工导入（F18）：body {title, subject, sections} 或 {json: 原文}。"""
        data = body
        if body.get("json"):
            try:
                data = json.loads(body["json"])
            except ValueError:
                return 400, {"error": "JSON 解析失败，请检查格式"}
            if isinstance(data, list) and len(data) == 1:
                data = data[0]
        if not self._validate_set(data, strict=True):
            return 400, {"error": "题组结构不合法：需要 subject(listening/reading)、title、"
                                  "sections[{material, questions[{no,type,stem,options?,answer}]}]，"
                                  "type ∈ choice/tfng/blank 且必须有答案"}
        data = dict(data)
        slug = re.sub(r'[\\/:*?"<>|\s]+', '-', data["title"])[:40] or "set"
        path = self._bank_dir() / f"manual-{slug}.json"
        i = 1
        while path.exists():
            path = self._bank_dir() / f"manual-{slug}-{i}.json"
            i += 1
        data.setdefault("id", path.stem)
        data["source"] = "manual"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        n = sum(len(sec["questions"]) for sec in data["sections"])
        return 201, {"id": data["id"], "file": path.name, "n_questions": n}

    def attempt_stats(self):
        """刷题历史 + 按科目累计正确率。"""
        items = self._ctx.db.query(
            "SELECT id, set_id, subject, date, total, correct FROM ielts_attempts"
            " ORDER BY id DESC LIMIT 50")
        by_subject = self._ctx.db.query(
            "SELECT subject, COUNT(*) n, SUM(correct) c, SUM(total) t"
            " FROM ielts_attempts GROUP BY subject")
        stats = [{"subject": r["subject"], "subject_cn": SUBJECT_CN.get(r["subject"]),
                  "attempts": r["n"], "accuracy": round(r["c"] / r["t"] * 100) if r["t"] else 0}
                 for r in by_subject]
        titles = {s["id"]: s["title"] for s in self._bank_sets()}
        for it in items:
            it["title"] = titles.get(it["set_id"], it["set_id"])
        return {"items": items, "stats": stats}


    # ================= 口语板块（v1.15：内置话题库+每日轮换+我的版本） =================
    @staticmethod
    def _speak_seeds(part=None):
        from app.services.ielts_speak_seed import SPEAK_P1, SPEAK_P2, SPEAK_P3
        pool = {2: SPEAK_P2, 1: SPEAK_P1, 3: SPEAK_P3}
        seeds = SPEAK_P1 + SPEAK_P2 + SPEAK_P3
        if part:
            return pool.get(part, [])
        return seeds

    def _speak_seed_index(self):
        return {s["id"]: s for s in self._speak_seeds()}

    def speak_bank(self, part=None):
        """seed 话题（含范文/我的版本）+ 用户自建话题合并视图。"""
        rows = self._ctx.db.query(
            "SELECT id, part, topic, freq, practiced, seed_id FROM ielts_topics"
            + (" WHERE part=?" if part else "") + " ORDER BY (practiced), freq DESC, id",
            (part,) if part else ())
        seeds = self._speak_seed_index()
        notes = {r["seed_id"]: r["text"] for r in self._ctx.db.query(
            "SELECT seed_id, text FROM ielts_speak_notes")}
        out, seen_seed = [], set()
        for r in rows:
            item = {"row_id": r["id"], "part": r["part"], "topic": r["topic"],
                    "freq": r["freq"], "practiced": r["practiced"],
                    "seed_id": r["seed_id"] or ""}
            if r["seed_id"] and r["seed_id"] in seeds:
                s = seeds[r["seed_id"]]
                item.update({"cue": s.get("cue"), "qa": s.get("qa"),
                             "sample": s.get("sample"), "vocab": s.get("vocab"),
                             "note": notes.get(r["seed_id"], "")})
                seen_seed.add(r["seed_id"])
            out.append(item)
        # 种子里还没入库的话题（新装/升级补齐前的兜底展示）
        for sid, s in seeds.items():
            if sid in seen_seed or (part and s["part"] != part):
                continue
            out.append({"row_id": None, "part": s["part"], "topic": s["topic"],
                        "freq": 0, "practiced": 0, "seed_id": sid,
                        "cue": s.get("cue"), "qa": s.get("qa"),
                        "sample": s.get("sample"), "vocab": s.get("vocab"),
                        "note": notes.get(sid, "")})
        return out

    def speak_daily(self):
        """今日话题：Part 2 池按 day_of_year 确定性轮换（同日稳定）。"""
        from datetime import datetime as _dt
        p2 = self._speak_seeds(2)
        doy = _dt.now().timetuple().tm_yday
        s = p2[doy % len(p2)]
        note = self._ctx.db.query_one(
            "SELECT text FROM ielts_speak_notes WHERE seed_id=?", (s["id"],))
        row = self._ctx.db.query_one(
            "SELECT id, practiced FROM ielts_topics WHERE seed_id=?", (s["id"],))
        return {"seed_id": s["id"], "topic": s["topic"], "cue": s["cue"],
                "sample": s["sample"], "vocab": s["vocab"],
                "note": note["text"] if note else "",
                "row_id": row["id"] if row else None,
                "practiced": row["practiced"] if row else 0,
                "day": _dt.now().strftime("%Y-%m-%d")}

    def speak_note(self, seed_id, text):
        """保存/清空"我的版本"。"""
        if not seed_id or seed_id not in self._speak_seed_index():
            return (400, {"error": "未知话题"})
        from app.core.timeutil import now
        text = (text or "").strip()
        if text:
            self._ctx.db.execute(
                "INSERT INTO ielts_speak_notes (seed_id, text, updated_at) VALUES (?,?,?)"
                " ON CONFLICT(seed_id) DO UPDATE SET text=excluded.text,"
                " updated_at=excluded.updated_at",
                (seed_id, text, now()))
        else:
            self._ctx.db.execute("DELETE FROM ielts_speak_notes WHERE seed_id=?", (seed_id,))
        return {"ok": True}


    # ================= 口语录音（v1.16：本机 data/ielts_recordings/{key}/） =================
    _REC_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")

    def _rec_dir(self, key):
        if not self._REC_SAFE.match(key or "") or ".." in (key or ""):
            return None
        d = self._ctx.data_dir / "ielts_recordings" / key
        d.mkdir(parents=True, exist_ok=True)
        return d

    def rec_list(self, key):
        d = self._rec_dir(key)
        if not d:
            return (400, {"error": "非法话题标识"})
        items = []
        for f in sorted(d.iterdir(), reverse=True):
            if f.is_file() and f.suffix in (".webm", ".ogg", ".mp4", ".m4a"):
                items.append({"name": f.name, "size": f.stat().st_size,
                              "ts": f.stem.replace(key + "-", "")})
        return {"items": items}

    def rec_save(self, key, ctype, raw):
        d = self._rec_dir(key)
        if not d:
            return (400, {"error": "非法话题标识"})
        ext = {"audio/webm": "webm", "audio/ogg": "ogg",
               "audio/mp4": "m4a", "audio/mpeg": "mp3"}.get((ctype or "").split(";")[0].strip())
        if not ext:
            return (400, {"error": f"不支持的音频类型：{ctype}"})
        if not raw or len(raw) < 1000:
            return (400, {"error": "录音太短或为空"})
        base = f"{key}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        name, i = f"{base}.{ext}", 1
        while (d / name).exists():      # 同秒多条录音防覆盖
            name, i = f"{base}-{i}.{ext}", i + 1
        (d / name).write_bytes(raw)
        return 201, {"ok": True, "name": name, "size": len(raw)}

    def rec_file(self, key, name):
        """→ (mimetype, path) 供传输层二进制直出；无效返回 None。"""
        d = self._rec_dir(key)
        if not d or not self._REC_SAFE.match(name or "") or not name.startswith(key + "-"):
            return None
        p = d / name
        if not p.is_file():
            return None
        return ({"webm": "audio/webm", "ogg": "audio/ogg",
                 "m4a": "audio/mp4", "mp3": "audio/mpeg"}[p.suffix[1:]], p)

    def rec_delete(self, key, name):
        d = self._rec_dir(key)
        if not d or not self._REC_SAFE.match(name or "") or not name.startswith(key + "-"):
            return (400, {"error": "非法文件名"})
        (d / name).unlink(missing_ok=True)
        return {"ok": True}


    # ================= 写作板块（v1.16：内置题库+每日任务+我的作文） =================
    @staticmethod
    def _write_seeds(task=None):
        from app.services.ielts_write_seed import WRITE_T1, WRITE_T2
        seeds = WRITE_T1 + WRITE_T2
        if task:
            return [s for s in seeds if s["task"] == task]
        return seeds

    def _write_notes(self):
        return {r["seed_id"]: r["text"] for r in self._ctx.db.query(
            "SELECT seed_id, text FROM ielts_write_notes")}

    def write_bank(self, task=None):
        notes = self._write_notes()
        return {"items": [{**s, "note": notes.get(s["id"], "")}
                          for s in self._write_seeds(task)]}

    def write_daily(self):
        from datetime import datetime as _dt
        doy = _dt.now().timetuple().tm_yday
        t2 = [s for s in self._write_seeds(2)]
        t1 = [s for s in self._write_seeds(1)]
        s2, s1 = t2[doy % len(t2)], t1[doy % len(t1)]
        notes = self._write_notes()
        mk = lambda s: {**s, "note": notes.get(s["id"], "")}
        return {"t2": mk(s2), "t1": mk(s1), "day": _dt.now().strftime("%Y-%m-%d")}

    def write_note(self, seed_id, text):
        from app.core.timeutil import now
        if not seed_id or seed_id not in {s["id"] for s in self._write_seeds()}:
            return (400, {"error": "未知题目"})
        text = (text or "").strip()
        if text:
            self._ctx.db.execute(
                "INSERT INTO ielts_write_notes (seed_id, text, updated_at) VALUES (?,?,?)"
                " ON CONFLICT(seed_id) DO UPDATE SET text=excluded.text,"
                " updated_at=excluded.updated_at",
                (seed_id, text, now()))
        else:
            self._ctx.db.execute("DELETE FROM ielts_write_notes WHERE seed_id=?", (seed_id,))
        return {"ok": True}


def register(ctx: AppContext):
    ctx.services.register(IeltsService.name, IeltsService(ctx))


def post_migrate(ctx: AppContext):
    """口语种子话题入库（INSERT OR IGNORE，不覆盖用户数据）。"""
    from app.services.ielts_speak_seed import SPEAK_P1, SPEAK_P2, SPEAK_P3
    for s in SPEAK_P1 + SPEAK_P2 + SPEAK_P3:
        row = ctx.db.query_one("SELECT id FROM ielts_topics WHERE seed_id=?", (s["id"],))
        if row:
            continue
        dup = ctx.db.query_one(
            "SELECT id FROM ielts_topics WHERE seed_id='' AND topic=? AND part=?",
            (s["topic"], s["part"]))
        if dup:   # 用户此前手建过同名话题 → 归属为该行，不新建
            ctx.db.execute("UPDATE ielts_topics SET seed_id=? WHERE id=?",
                           (s["id"], dup["id"]))
            continue
        ctx.db.execute(
            "INSERT INTO ielts_topics (part, topic, freq, practiced, seed_id)"
            " VALUES (?,?,0,0,?)", (s["part"], s["topic"], s["id"]))
