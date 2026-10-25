# -*- coding: utf-8 -*-
"""目标域：目标/里程碑/进度/倒计时 + 预置种子（DESIGN 对象3）。"""
from datetime import date
from app.core.registry import AppContext

MIGRATIONS = [
    ("0004_goal", """
        CREATE TABLE IF NOT EXISTS goal_goals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline    TEXT,
            sort        INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS goal_milestones (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id    INTEGER NOT NULL,
            title      TEXT NOT NULL,
            weight     INTEGER DEFAULT 1,
            done_count INTEGER DEFAULT 0,
            total      INTEGER DEFAULT 1,
            sort       INTEGER DEFAULT 0
        );
    """),
    ("0018_goal_archive", """
        ALTER TABLE goal_goals ADD COLUMN archived INTEGER NOT NULL DEFAULT 0;
    """),
]

# 预置目标（需求 §3.3）：四条主线，首次一键初始化
SEED = [
    ("后端日常实习准备", "八股 + 算法 + 项目，瞄准成都日常实习 HC", None, [
        ("八股复习（网络/OS/MySQL/Redis）", 3), ("算法刷题 200 题", 200), ("项目与简历打磨", 4),
    ]),
    ("小论文", "选题 → 文献 → 实验 → 初稿 → 投稿", None, [
        ("选题", 1), ("文献调研", 1), ("实验", 1), ("初稿", 1), ("投稿", 1),
    ]),
    ("Agent 项目作品", "智能运维 Agent 等差异化项目，为研二 AI 实习铺路", None, [
        ("选题与技术方案", 1), ("开发实现", 1), ("部署上线与 README", 1),
    ]),
    ("雅思 7.0+", "长线基础积累，考试时间未定（不设倒计时）", None, [
        ("核心词汇", 1), ("听力精听", 1), ("阅读训练", 1), ("写作与口语", 1),
    ]),
]


class GoalService:
    name = "goal_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def list(self, archived=False):
        goals = self._ctx.db.query(
            "SELECT * FROM goal_goals WHERE archived=? ORDER BY sort, id",
            (1 if archived else 0,))
        for g in goals:
            ms = self._ctx.db.query(
                "SELECT * FROM goal_milestones WHERE goal_id=? ORDER BY sort, id", (g["id"],))
            g["milestones"] = ms
            g["progress"] = self._calc_progress(ms)
            if g["deadline"]:
                g["days_left"] = (date.fromisoformat(g["deadline"]) - date.today()).days
            else:
                g["days_left"] = None
        return goals

    def set_archived(self, goal_id, archived: bool):
        self._ctx.db.execute(
            "UPDATE goal_goals SET archived=? WHERE id=?", (1 if archived else 0, goal_id))
        return True

    def delete(self, goal_id):
        """确认后彻底删除：目标 + 里程碑（任务上的里程碑引用置空由 task 域自理）。"""
        self._ctx.db.execute("DELETE FROM goal_milestones WHERE goal_id=?", (goal_id,))
        self._ctx.db.execute("DELETE FROM goal_goals WHERE id=?", (goal_id,))
        return True

    def bump_milestone(self, milestone_id, delta=1):
        """手动推进/回退里程碑（小论文等页面用；delta 可为负）。"""
        self._ctx.db.execute(
            "UPDATE goal_milestones SET done_count = MAX(0, MIN(total, done_count + ?))"
            " WHERE id=?", (delta, milestone_id))

    @staticmethod
    def _calc_progress(ms):
        total_w = sum(m["weight"] for m in ms) or 1
        got = sum(m["weight"] * (m["done_count"] / m["total"] if m["total"] else 1) for m in ms)
        return round(got / total_w * 100)

    def set_deadline(self, goal_id, deadline):
        self._ctx.db.execute("UPDATE goal_goals SET deadline=? WHERE id=?", (deadline, goal_id))
        return True

    def create(self, title, description="", deadline=None, milestones=None):
        gid = self._ctx.db.execute(
            "INSERT INTO goal_goals (title, description, deadline, sort)"
            " VALUES (?,?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM goal_goals))",
            (title, description, deadline))
        for i, item in enumerate(milestones or []):
            mtitle, total = (item if isinstance(item, (list, tuple)) else (item, 1))
            self._ctx.db.execute(
                "INSERT INTO goal_milestones (goal_id,title,total,sort) VALUES (?,?,?,?)",
                (gid, mtitle, total, i))
        return gid

    def record_progress(self, milestone_id, delta=1):
        """任务完成时推进里程碑进度（由 task 域调用）。"""
        self._ctx.db.execute(
            "UPDATE goal_milestones SET done_count = MIN(total, done_count + ?) WHERE id=?",
            (delta, milestone_id))

    def seed(self):
        """幂等初始化预置目标。"""
        if self._ctx.db.query_one("SELECT COUNT(*) n FROM goal_goals")["n"] > 0:
            return {"seeded": False, "msg": "已有目标数据，跳过"}
        for gi, (title, desc, deadline, ms) in enumerate(SEED):
            gid = self._ctx.db.execute(
                "INSERT INTO goal_goals (title,description,deadline,sort) VALUES (?,?,?,?)",
                (title, desc, deadline, gi))
            for mi, (mtitle, total) in enumerate(ms):
                self._ctx.db.execute(
                    "INSERT INTO goal_milestones (goal_id,title,weight,total,sort) VALUES (?,?,?,?,?)",
                    (gid, mtitle, 1, total, mi))
        return {"seeded": True, "goals": len(SEED)}

    def urgent(self, days=30, limit=3):
        """临近截止/长期停滞的里程碑（供规划引擎）。"""
        goals = self.list()
        out = []
        for g in goals:
            if g["days_left"] is not None and g["days_left"] <= days and g["progress"] < 100:
                out.append({"goal": g["title"], "days_left": g["days_left"], "progress": g["progress"]})
        return out[:limit]


def register(ctx: AppContext):
    ctx.services.register(GoalService.name, GoalService(ctx))
