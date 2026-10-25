# -*- coding: utf-8 -*-
"""学习闭环域（DESIGN v2.0 F12/F13，卡片模型移植自 leetcode/learning skill）：

- 阅读文章时向 AI 提问 → 自动沉淀知识卡片（问/答/记忆点/参考文章），本地保存
- 复习模式：到期卡片按 Ebbinghaus 曲线（1→2→4→7→15→30 天）出题；
  AI 可用时生成变体题考我，不可用时降级为"显示问题→回想→翻答案→自评"
"""
import json
from datetime import date, timedelta

from app.core.registry import AppContext
from app.core.timeutil import today

MIGRATIONS = [
    ("0014_learn", """
        CREATE TABLE IF NOT EXISTS learn_cards (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter    TEXT DEFAULT '待归档',
            ctype      TEXT DEFAULT 'knowledge',   -- knowledge/bug/syntax/design
            title      TEXT NOT NULL,
            q          TEXT NOT NULL,
            a          TEXT DEFAULT '',
            point      TEXT DEFAULT '',
            summary    TEXT DEFAULT '',
            ref_path   TEXT DEFAULT '',
            ref_title  TEXT DEFAULT '',
            library    TEXT DEFAULT 'bagu',
            created_at TEXT NOT NULL,
            stage      INTEGER DEFAULT 0,          -- 0..6 记忆曲线阶段
            due_date   TEXT NOT NULL,
            status     TEXT DEFAULT 'todo'         -- todo/weak/done
        );
    """),
]

INTERVALS = [1, 2, 4, 7, 15, 30]  # 阶段 i 答对 → 下次 = 今天 + INTERVALS[i]


class LearnService:
    name = "learn_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    # ---- 提问沉淀（F12） ----
    def ask(self, question, ref_path=None, library="bagu"):
        """带文章上下文提问：AI 答则存完整卡；无 AI 存参考回答卡（复习时自测）。"""
        context = ""
        if ref_path:
            art = self._ctx.services.get("kb_service").article(ref_path)
            if art:
                # 当前阅读文章的正文节选为主上下文（比检索片段信息量完整得多）
                context = f"\n\n当前阅读文章《{art['title']}》正文节选：\n{art['body'][:4000]}"
        # v2.2：库内其他文章的相关分块（混合检索，F21）作为补充资料
        try:
            chunks = [c for c in self._ctx.services.get("kb_service")
                      .rag_retrieve(question, library=library, k=3)
                      if c["relpath"] != ref_path]
            if chunks:
                context += "\n\n库内相关资料：\n" + "\n\n".join(
                    f"《{c['title']}{' · ' + c['heading'] if c['heading'] else ''}》：\n{c['text']}"
                    for c in chunks)
        except Exception:
            pass  # 检索异常不阻塞提问
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是面试八股辅导。用简洁中文回答，先给一句话结论再展开；"
                "最后单独一行输出'记忆点：<不超过30字>'。"},
            {"role": "user", "content": question + context},
        ], feature="学习卡片")
        title = question.strip()[:40]
        answer, point = "", ""
        if ai:
            answer = ai.strip()
            m = ai.rsplit("记忆点：", 1)
            if len(m) == 2:
                answer, point = m[0].strip(), m[1].strip().splitlines()[0][:40]
        else:
            # F12 v2.1 降级：无 AI 时用检索块拼参考回答（卡片可后续补答）
            chunks = self._ctx.services.get("kb_service").rag_retrieve(
                question, library=library, k=3)
            if chunks:
                answer = "（AI 未配置——知识库参考段落）\n\n" + "\n\n".join(
                    f"《{c['title']}{' · ' + c['heading'] if c['heading'] else ''}》："
                    f"{c['text'][:120]}…" for c in chunks)
        meta = (self._ctx.services.get("kb_service").meta(ref_path)
                if ref_path else None) or {}
        card = self.add_card(
            title=title, q=question, a=answer, point=point, summary=title,
            ref_path=ref_path or "", library=library,
            chapter=meta.get("category") or "待归档")
        return {"card": card, "ai_used": ai is not None}

    def add_card(self, title, q, a="", point="", summary="", ref_path="",
                 ref_title="", library="bagu", chapter="待归档", ctype="knowledge"):
        from app.core.timeutil import now
        cid = self._ctx.db.execute(
            "INSERT INTO learn_cards (chapter, ctype, title, q, a, point, summary,"
            " ref_path, ref_title, library, created_at, due_date)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (chapter, ctype, title, q, a, point, summary or title, ref_path, ref_title,
             library, now(), (date.today() + timedelta(days=1)).isoformat()))
        return self.get(cid)

    def get(self, cid):
        return self._ctx.db.query_one("SELECT * FROM learn_cards WHERE id=?", (cid,))

    def update(self, cid, **f):
        allowed = {"title", "q", "a", "point", "summary", "chapter"}
        sets = [f"{k}=?" for k in f if k in allowed]
        if not sets:
            return self.get(cid)
        self._ctx.db.execute(
            f"UPDATE learn_cards SET {', '.join(sets)} WHERE id=?",
            [f[k] for k in f if k in allowed] + [cid])
        return self.get(cid)

    def delete(self, cid):
        self._ctx.db.execute("DELETE FROM learn_cards WHERE id=?", (cid,))

    def cards(self, limit=200):
        return self._ctx.db.query(
            "SELECT * FROM learn_cards ORDER BY id DESC LIMIT ?", (limit,))

    def due_count(self):
        return self._ctx.db.query_one(
            "SELECT COUNT(*) n FROM learn_cards WHERE due_date <= ? AND status != 'done'",
            (today(),))["n"]

    # ---- 复习（F13） ----
    def due_cards(self, n=10):
        """到期优先，不足补最旧未掌握。"""
        due = self._ctx.db.query(
            "SELECT * FROM learn_cards WHERE status != 'done' AND due_date <= ?"
            " ORDER BY due_date LIMIT ?", (today(), n))
        if len(due) < n:
            extra = self._ctx.db.query(
                "SELECT * FROM learn_cards WHERE status != 'done' AND due_date > ?"
                " ORDER BY stage, due_date LIMIT ?", (today(), n - len(due)))
            due += extra
        return due

    def quiz(self, card):
        """AI 出变体题；降级返回原卡自测。"""
        ai = self._ctx.ai.chat([
            {"role": "system", "content":
                "你是面试官。基于给定知识卡片出 1 道面试题考我（可以换角度提问），"
                "只输出题目本身，不超过60字，不要给答案。"},
            {"role": "user", "content":
                f"卡片：问题={card['q']}；答案={card['a'][:300]}；记忆点={card['point']}"},
        ], feature="学习卡片")
        return {"card": card, "quiz": (ai or card["q"]).strip(), "ai_generated": ai is not None}

    def review(self, cid, result):
        """pass 推进 / fuzzy 原地 / fail 归零；更新下次复习日。"""
        card = self.get(cid)
        if not card:
            return None
        if result == "pass":
            stage = min(card["stage"] + 1, len(INTERVALS))
            gap = INTERVALS[stage - 1] if stage > 0 else 1
            status = "done" if stage >= len(INTERVALS) else "todo"
        elif result == "fuzzy":
            stage = card["stage"]
            gap = INTERVALS[stage - 1] if stage > 0 else 1
            status = "weak"
        else:  # fail
            stage, gap, status = 0, 1, "weak"
        due = (date.today() + timedelta(days=gap)).isoformat()
        self._ctx.db.execute(
            "UPDATE learn_cards SET stage=?, due_date=?, status=? WHERE id=?",
            (stage, due, status, cid))
        self._ctx.events.publish("learn.review_done",
                                 {"card_id": cid, "result": result})
        return self.get(cid)

    def stats(self):
        rows = self._ctx.db.query(
            "SELECT status, COUNT(*) n FROM learn_cards GROUP BY status")
        m = {r["status"]: r["n"] for r in rows}
        return {"total": sum(m.values()), "due": self.due_count(),
                "weak": m.get("weak", 0), "done": m.get("done", 0)}


def register(ctx: AppContext):
    ctx.services.register(LearnService.name, LearnService(ctx))
