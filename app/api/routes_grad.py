# -*- coding: utf-8 -*-
"""研究生路由：课程（v2.4 详情：文件/复习/作业）/ 组会 / 导师任务 / 文献。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    grad = lambda: ctx.services.get("grad_service")
    paper = lambda: ctx.services.get("paper_service")

    # ---- 课程 ----
    def courses(ctx: AppContext, params, body, query):
        return {"courses": grad().courses()}

    def add_course(ctx: AppContext, params, body, query):
        day = body.get("day_of_week")
        day = None if day is None or int(day) < 0 else int(day)
        try:
            cid = grad().add_course(
                body["name"], day,
                body.get("start_time", ""), body.get("end_time", ""),
                body.get("place", ""), body.get("weeks", ""), body.get("folder_path", ""))
        except ValueError as e:
            return 400, {"error": str(e)}
        return 201, {"id": cid}

    def course_detail(ctx: AppContext, params, body, query):
        d = grad().course_detail(int(params["id"]))
        return d or (404, {"error": "课程不存在"})

    def update_course(ctx: AppContext, params, body, query):
        try:
            c = grad().update_course(int(params["id"]),
                                     name=body.get("name"),
                                     folder_path=body.get("folder_path"),
                                     day_of_week=body.get("day_of_week"),
                                     start_time=body.get("start_time"),
                                     end_time=body.get("end_time"),
                                     place=body.get("place"), weeks=body.get("weeks"))
        except ValueError as e:
            return 400, {"error": str(e)}
        return c or (404, {"error": "课程不存在"})

    def del_course(ctx: AppContext, params, body, query):
        grad().delete_course(int(params["id"]))
        return {"ok": True}

    def del_meeting(ctx: AppContext, params, body, query):
        grad().delete_meeting(int(params["id"]))
        return {"ok": True}

    def del_advisor(ctx: AppContext, params, body, query):
        grad().delete_advisor_task(int(params["id"]))
        return {"ok": True}

    # ---- 课程文件（F23） ----
    def add_file(ctx: AppContext, params, body, query):
        if not body.get("path"):
            return 400, {"error": "path 必填"}
        try:
            fid = grad().add_file(int(params["id"]), body["path"], body.get("name", ""))
        except ValueError as e:
            return 400, {"error": str(e)}
        return 201, {"id": fid}

    def del_file(ctx: AppContext, params, body, query):
        grad().delete_file(int(params["id"]), int(params["fid"]))
        return {"ok": True}

    def open_file(ctx: AppContext, params, body, query):
        if not body.get("path"):
            return 400, {"error": "path 必填"}
        try:
            grad().open_file(int(params["id"]), body["path"])
        except ValueError as e:
            return 400, {"error": str(e)}
        return {"ok": True}

    def review_file(ctx: AppContext, params, body, query):
        if not body.get("path"):
            return 400, {"error": "path 必填"}
        try:
            grad().set_file_review(int(params["id"]), body["path"],
                                   bool(body.get("reviewed", True)))
        except ValueError as e:
            return 400, {"error": str(e)}
        return {"ok": True}

    # ---- 作业（F24） ----
    def add_assignment(ctx: AppContext, params, body, query):
        try:
            aid = grad().add_assignment(int(params["id"]), body.get("title", ""),
                                        body.get("due_date", ""), body.get("note", ""),
                                        body.get("file_ref", ""))
        except ValueError as e:
            return 400, {"error": str(e)}
        return 201, {"id": aid}

    def update_assignment(ctx: AppContext, params, body, query):
        try:
            a = grad().update_assignment(int(params["id"]), **body)
        except ValueError as e:
            return 400, {"error": str(e)}
        return a or (404, {"error": "作业不存在"})

    def del_assignment(ctx: AppContext, params, body, query):
        grad().delete_assignment(int(params["id"]))
        return {"ok": True}

    def convert_assignment(ctx: AppContext, params, body, query):
        try:
            t = grad().convert_assignment(int(params["id"]))
        except ValueError as e:
            return 400, {"error": str(e)}
        return t or (404, {"error": "作业不存在"})

    # ---- 学习助手 / 课程 AI 问答 / AI 考我（v2.15 F27/F28/F29） ----
    def install_skill(ctx: AppContext, params, body, query):
        try:
            r = grad().install_skill(int(params["id"]))
        except ValueError as e:
            return 400, {"error": str(e)}
        return r

    def course_ask(ctx: AppContext, params, body, query):
        if not (body.get("question") or "").strip():
            return 400, {"error": "question 必填"}
        try:
            return grad().course_ask(int(params["id"]), body["question"])
        except ValueError as e:
            return 400, {"error": str(e)}

    def course_quiz(ctx: AppContext, params, body, query):
        try:
            return grad().course_quiz(int(params["id"]), body.get("n", 5))
        except ValueError as e:
            return 400, {"error": str(e)}

    def course_quiz_grade(ctx: AppContext, params, body, query):
        try:
            return grad().course_quiz_grade(
                int(params["id"]), body.get("question", ""),
                body.get("answer", ""), body.get("ref", ""))
        except ValueError as e:
            return 400, {"error": str(e)}

    # ---- 组会 ----
    def meetings(ctx: AppContext, params, body, query):
        return {"meetings": grad().meetings()}

    def add_meeting(ctx: AppContext, params, body, query):
        mid = grad().add_meeting(
            body["meet_date"], body.get("title", "组会"),
            body.get("notes", ""), body.get("my_todos", ""))
        return 201, {"id": mid}

    def update_meeting(ctx: AppContext, params, body, query):
        grad().update_meeting(int(params["id"]),
                              notes=body.get("notes"), my_todos=body.get("my_todos"))
        return {"ok": True}

    # ---- 导师任务 ----
    def advisor(ctx: AppContext, params, body, query):
        status = query.get("status")
        return {"items": grad().advisor_tasks(status)}

    def add_advisor(ctx: AppContext, params, body, query):
        if not body.get("content"):
            return 400, {"error": "content 必填"}
        aid = grad().add_advisor_task(body["content"])
        return 201, {"id": aid}

    def convert_advisor(ctx: AppContext, params, body, query):
        t = grad().convert_advisor_task(int(params["id"]))
        return t or (400, {"error": "任务不存在或已转化"})

    # ---- 文献 ----
    def papers(ctx: AppContext, params, body, query):
        return {"papers": paper().list(query.get("status"))}

    def import_papers(ctx: AppContext, params, body, query):
        text = body.get("text", "")
        if not text.strip():
            return 400, {"error": "text 必填（Zotero BBT 导出的 JSON 内容）"}
        return paper().import_from_text(text)

    def set_status(ctx: AppContext, params, body, query):
        paper().set_status(int(params["id"]), body["status"])
        return {"ok": True}

    def add_note(ctx: AppContext, params, body, query):
        nid = paper().add_note(int(params["id"]), body["content"])
        return 201, {"id": nid}

    def notes(ctx: AppContext, params, body, query):
        return {"notes": paper().notes(int(params["id"]))}

    def del_paper(ctx: AppContext, params, body, query):
        paper().delete_paper(int(params["id"]))     # v1.19：级联笔记
        return {"ok": True}

    def del_paper_note(ctx: AppContext, params, body, query):
        paper().delete_note(int(params["id"]))      # v1.19
        return {"ok": True}

    # 课程
    router.get("/api/grad/courses", courses)
    router.post("/api/grad/courses", add_course)
    router.get("/api/grad/courses/{id}", course_detail)
    router.put("/api/grad/courses/{id}", update_course)
    router.delete("/api/grad/courses/{id}", del_course)
    # 课程文件（F23）
    router.post("/api/grad/courses/{id}/files", add_file)
    router.delete("/api/grad/courses/{id}/files/{fid}", del_file)
    router.post("/api/grad/courses/{id}/open", open_file)
    router.post("/api/grad/courses/{id}/review", review_file)
    # 作业（F24）
    router.post("/api/grad/courses/{id}/assignments", add_assignment)
    router.put("/api/grad/assignments/{id}", update_assignment)
    router.delete("/api/grad/assignments/{id}", del_assignment)
    router.post("/api/grad/assignments/{id}/convert", convert_assignment)
    # 学习助手 / 问 AI / AI 考我（v2.15）
    router.post("/api/grad/courses/{id}/skill", install_skill)
    router.post("/api/grad/courses/{id}/ask", course_ask)
    router.post("/api/grad/courses/{id}/quiz", course_quiz)
    router.post("/api/grad/courses/{id}/quiz/grade", course_quiz_grade)
    # 组会 / 导师 / 文献
    router.get("/api/grad/meetings", meetings)
    router.post("/api/grad/meetings", add_meeting)
    router.put("/api/grad/meetings/{id}", update_meeting)
    router.delete("/api/grad/meetings/{id}", del_meeting)
    router.get("/api/grad/advisor", advisor)
    router.post("/api/grad/advisor", add_advisor)
    router.post("/api/grad/advisor/{id}/convert", convert_advisor)
    router.delete("/api/grad/advisor/{id}", del_advisor)
    router.get("/api/papers", papers)
    router.post("/api/papers/import", import_papers)
    router.put("/api/papers/{id}/status", set_status)
    router.post("/api/papers/{id}/notes", add_note)
    router.get("/api/papers/{id}/notes", notes)
    router.delete("/api/papers/{id}", del_paper)            # v1.19
    router.delete("/api/papers/notes/{id}", del_paper_note)  # v1.19
