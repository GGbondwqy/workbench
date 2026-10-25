# -*- coding: utf-8 -*-
"""词汇域：单词 SRS（简化记忆曲线）+ 英语训练打卡（DESIGN 对象6/7，流程 F4）。

间隔规则（设计参数集中此处，可调）：
  评分 0忘了 → 明天再出现；1模糊 → 后天；2记得 → 间隔×2.2；3秒答 → 间隔×3.2（封顶 60 天）
"""
from app.core.registry import AppContext
from app.core.timeutil import today

MIGRATIONS = [
    ("0007_vocab", """
        CREATE TABLE IF NOT EXISTS vocab_words (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            word    TEXT NOT NULL UNIQUE,
            meaning TEXT DEFAULT '',
            source  TEXT DEFAULT 'builtin',   -- builtin/自定义
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vocab_records (
            word_id      INTEGER PRIMARY KEY,
            due_date     TEXT NOT NULL,
            interval_days INTEGER DEFAULT 0,
            reps         INTEGER DEFAULT 0,
            last_grade   INTEGER,
            updated_at   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vocab_practice (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            date    TEXT NOT NULL,
            kind    TEXT NOT NULL,             -- listening/reading/writing/speaking
            minutes INTEGER DEFAULT 0,
            note    TEXT DEFAULT ''
        );
    """),
]

FACTORS = {0: None, 1: None, 2: 2.2, 3: 3.2}
MAX_INTERVAL = 60
DAILY_NEW_LIMIT = 10  # 每日新词上限（队列里新词最多混入这么多）


def _next_interval(interval, grade):
    if grade == 0:
        return 1
    if grade == 1:
        return 2 if interval < 2 else max(1, interval // 2)
    factor = FACTORS[grade]
    return min(MAX_INTERVAL, max(1, int((interval or 1) * factor)))


class VocabService:
    name = "vocab_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 词库 ----
    def add_word(self, word, meaning, source="custom"):
        from app.core.timeutil import now
        try:
            wid = self._ctx.db.execute(
                "INSERT INTO vocab_words (word, meaning, source, created_at) VALUES (?,?,?,?)",
                (word.strip(), meaning.strip(), source, now()))
            self._ctx.db.execute(
                "INSERT INTO vocab_records (word_id, due_date, interval_days, reps, updated_at)"
                " VALUES (?,?,0,0,?)", (wid, today(), now()))
            return wid
        except Exception:
            return None  # 重复词忽略

    def import_words(self, lines):
        """粘贴导入：每行 "word 释义"（空格/制表符分隔），返回成功数。"""
        n = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            word = parts[0]
            meaning = parts[1] if len(parts) > 1 else ""
            if self.add_word(word, meaning, "custom") is not None:
                n += 1
        return {"imported": n}

    def counts(self):
        row = self._ctx.db.query_one("SELECT COUNT(*) n FROM vocab_words")
        return row["n"]

    # ---- 复习队列 ----
    def due_queue(self, limit=50):
        """到期队列：到期老词优先，再补少量新词。"""
        due = self._ctx.db.query(
            "SELECT w.id, w.word, w.meaning, r.due_date, r.reps FROM vocab_words w"
            " JOIN vocab_records r ON r.word_id = w.id"
            " WHERE r.due_date <= ? AND r.reps > 0 ORDER BY r.due_date LIMIT ?", (today(), limit))
        fresh = self._ctx.db.query(
            "SELECT w.id, w.word, w.meaning, r.due_date, r.reps FROM vocab_words w"
            " JOIN vocab_records r ON r.word_id = w.id"
            " WHERE r.reps = 0 ORDER BY w.id LIMIT ?", (DAILY_NEW_LIMIT,))
        return due + fresh[: max(0, limit - len(due))]

    def due_count(self):
        return len(self.due_queue(limit=500))

    def review(self, word_id, grade):
        from app.core.timeutil import now
        rec = self._ctx.db.query_one("SELECT * FROM vocab_records WHERE word_id=?", (word_id,))
        interval = _next_interval(rec["interval_days"] if rec else 0, grade)
        from datetime import date, timedelta
        due = (date.today() + timedelta(days=interval)).isoformat()
        self._ctx.db.execute(
            "UPDATE vocab_records SET due_date=?, interval_days=?, reps=reps+1,"
            " last_grade=?, updated_at=? WHERE word_id=?",
            (due, interval, grade, now(), word_id))
        return {"word_id": word_id, "next_due": due, "interval": interval}

    def finish_session(self, count):
        self._ctx.events.publish("vocab.review_done", {"count": count})
        return {"ok": True}

    # ---- 训练打卡 ----
    def add_practice(self, day, kind, minutes, note=""):
        pid = self._ctx.db.execute(
            "INSERT INTO vocab_practice (date, kind, minutes, note) VALUES (?,?,?,?)",
            (day, kind, minutes, note))
        return pid

    def practices(self, limit=30):
        return self._ctx.db.query(
            "SELECT * FROM vocab_practice ORDER BY date DESC, id DESC LIMIT ?", (limit,))

    def reviews_between(self, start, end):
        """[start,end] 复习次数（周报统计：近似用 reps 增量不可得，改记 practice + 队列口径简化为打卡天数）。"""
        row = self._ctx.db.query_one(
            "SELECT COUNT(*) n FROM vocab_practice WHERE date BETWEEN ? AND ?", (start, end))
        return row["n"]


def register(ctx: AppContext):
    ctx.services.register(VocabService.name, VocabService(ctx))


def post_migrate(ctx: AppContext):
    """迁移完成后播种内置雅思核心词（幂等）。"""
    svc = ctx.services.get(VocabService.name)
    if svc.counts() == 0:
        from app.services import vocab_seed
        for w, m in vocab_seed.IELTS_CORE:
            svc.add_word(w, m, "builtin")
