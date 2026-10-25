# -*- coding: utf-8 -*-
"""规划引擎（业务逻辑层的调度核心，DESIGN F1）：

generate(date) 汇聚各域到期事项 → 规则生成"今日三件事 + 学习安排建议"；
AI 可用时升级为 AI 生成（带理由），不可用时纯规则。
confirm(date, items) 将确认后的建议落库为任务与学习日程块。

依赖的域全部经 ctx.services 注册表查询（底层隔离规则），本服务不知道它们的存在方式。
"""
from app.core.registry import AppContext
from app.core.timeutil import today


class PlanService:
    name = "plan_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def generate(self, date=None):
        date = date or today()
        s = self._ctx.services

        # 1) 收集各域"到期事项"（全部经注册表查询，域未上线自动跳过）
        #    优先级：面试临近 > 模考临近 > 导师任务 > 复习卡片到期 > 八股计划 > 目标临近 > 未完成任务
        items = []

        itv = s.try_get("interview_service")
        if itv:
            for u in itv.urgent(days=3):
                items.append({"kind": "interview", "priority": 0,
                              "title": f"准备面试：{u['company']} {u['round'] or ''}（{u['when']}）",
                              "est": 60, "reason": f"还有 {u['days_left']} 天，最高优先"})

        ielts = s.try_get("ielts_service")
        if ielts:
            for m in ielts.upcoming_mocks(3):
                items.append({"kind": "mock", "priority": 0,
                              "title": f"雅思模考（{m['date']}，{m['kind']}）",
                              "est": 180, "reason": f"还有 {m['days_left']} 天"})
            dl = ielts.days_left()
            if dl is not None and 0 <= dl <= 30:
                items.append({"kind": "ielts_exam", "priority": 1,
                              "title": f"雅思冲刺（距考试 {dl} 天）：薄弱题型专项",
                              "est": 60, "reason": "考试临近"})

        grad = s.try_get("grad_service")
        pending = grad.advisor_tasks("pending") if grad else []
        if pending:
            items.append({"kind": "advisor", "priority": 1,
                          "title": f"导师任务：{pending[0]['content'][:30]}",
                          "est": 60, "reason": "导师布置，优先处理"})

        learn = s.try_get("learn_service")
        if learn:
            due_n = learn.due_count()
            if due_n:
                items.append({"kind": "review", "priority": 2,
                              "title": f"复习知识卡片 {due_n} 张（八股问答积累）",
                              "est": 20, "reason": "记忆曲线到期"})

        career = s.try_get("career_service")
        kb_plan = {"available": False}
        if career:
            kb_plan = career.kb_plan(daily=2)
            if kb_plan.get("available") and kb_plan.get("items"):
                titles = "、".join(i["title"][:18] for i in kb_plan["items"])
                items.append({"kind": "kb", "priority": 3,
                              "title": f"八股精读 {len(kb_plan['items'])} 篇（{titles}…）",
                              "est": 40, "reason": f"剩余 {kb_plan['remaining']} 篇"})

        goal = s.try_get("goal_service")
        if goal:
            for u in goal.urgent():
                items.append({"kind": "goal", "priority": 4,
                              "title": f"推进目标「{u['goal']}」（{u['progress']}%，剩 {u['days_left']} 天）",
                              "est": 60, "reason": "临近截止"})

        task = s.try_get("task_service")
        today_open = [t for t in (task.list(date=date) if task else []) if t["status"] != "done"]
        for t in today_open[:2]:
            items.append({"kind": "task", "priority": 2,
                          "title": f"继续：{t['title'][:30]}",
                          "est": t["est_minutes"] or 45, "reason": "今日未完成"})

        # 2) 规则排序取前三 + 空闲时段
        items.sort(key=lambda x: x["priority"])
        top3 = items[:3]

        schedule = s.try_get("schedule_service")
        slots = schedule.free_slots(date) if schedule else []

        # 3) AI 升级（可用时给理由）
        ai_tip = None
        if top3 and self._ctx.ai.status()["configured"]:
            ai_tip = self._ctx.ai.chat([
                {"role": "system", "content": "用一两句话鼓励式点评今日计划安排，不超过60字。"},
                {"role": "user", "content": "今日建议：" + "；".join(i["title"] for i in top3)}], feature="每日建议")

        return {
            "date": date,
            "suggestions": top3,
            "all_items": items,
            "free_slots": slots,
            "ai_tip": ai_tip,
            "confirmed_hint": bool(today_open),
        }

    def confirm(self, date, items):
        """用户确认建议 → 落库任务（v2.1：不再生成学习日程块，时间自由安排）。"""
        date = date or today()
        s = self._ctx.services
        created_tasks = []
        for it in items:
            if not it.get("title"):
                continue
            task = s.get("task_service").create(
                title=it["title"], plan_date=date,
                priority=it.get("priority", "mid"),
                est_minutes=int(it.get("est") or 45), source="plan",
                milestone_id=it.get("milestone_id"))
            created_tasks.append(task)
        return {"tasks": created_tasks}

    def dashboard(self, date=None):
        """首页聚合数据（调度权在业务逻辑层：UI 只发一次请求）。
        v2.1 精简：移除时间轴/习惯/日志/周统计（复盘功能删除、时间轴取消）。
        v2.4 精简：移除建议字段——三件事卡片已删，不再每次打开首页触发
        generate()（其内部含一次 AI 点评调用）。generate/confirm 服务保留。"""
        date = date or today()
        s = self._ctx.services
        task = s.try_get("task_service")
        goal = s.try_get("goal_service")
        career = s.try_get("career_service")

        return {
            "date": date,
            "tasks": task.list(date=date, limit=50) if task else [],
            "task_stats": task.stats(date) if task else {"total": 0, "done": 0},
            "review_due": (s.try_get("learn_service").due_count()
                           if s.try_get("learn_service") else 0),
            "goals": goal.list() if goal else [],
            "kb_plan": career.kb_plan(daily=2) if career else {"available": False},
            "upcoming_interviews": (s.try_get("interview_service").urgent(7)
                                    if s.try_get("interview_service") else []),
            "upcoming_mocks": (s.try_get("ielts_service").upcoming_mocks(7)
                               if s.try_get("ielts_service") else []),
        }


def register(ctx: AppContext):
    ctx.services.register(PlanService.name, PlanService(ctx))
