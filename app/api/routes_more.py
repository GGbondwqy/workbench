# -*- coding: utf-8 -*-
"""项目 / 面试 / 雅思 / 力扣路由。"""
from app.core.registry import AppContext  # noqa: F401


def register_routes(router, ctx):
    # ================= 项目 =================
    P = lambda: ctx.services.get("project_service")

    def projects(ctx: AppContext, params, body, query):
        return {"projects": P().list(), "archived": P().list(archived=True)}

    def add_project(ctx: AppContext, params, body, query):
        if not body.get("name"):
            return 400, {"error": "name 必填"}
        p = P().create(body["name"], body.get("description", ""), body.get("status", "building"))
        return 201, p

    def set_status(ctx: AppContext, params, body, query):
        P().set_status(int(params["id"]), body["status"])
        return {"ok": True}

    def archive_project(ctx: AppContext, params, body, query):
        P().archive(int(params["id"]), bool(body.get("archived", True)))
        return {"ok": True}

    def bump_ms(ctx: AppContext, params, body, query):
        P().bump_milestone(int(params["id"]))
        return {"ok": True}

    def del_project(ctx: AppContext, params, body, query):
        P().delete(int(params["id"]))
        return {"ok": True}

    def items(ctx: AppContext, params, body, query):
        return {"items": P().items(int(params["id"]), query.get("kind", "stack"))}

    def add_item(ctx: AppContext, params, body, query):
        iid = P().add_item(int(params["id"]), body["kind"], body.get("title", ""),
                           body.get("content", ""), body.get("extra", ""))
        return 201, {"id": iid}

    def upd_item(ctx: AppContext, params, body, query):
        P().update_item(int(params["id"]), content=body.get("content"),
                        title=body.get("title"), extra=body.get("extra"))
        return {"ok": True}

    def del_item(ctx: AppContext, params, body, query):
        P().delete_item(int(params["id"]))
        return {"ok": True}

    def resumes(ctx: AppContext, params, body, query):
        return {"items": P().resumes()}

    router.get("/api/projects", projects)
    router.post("/api/projects", add_project)
    router.put("/api/projects/{id}/status", set_status)
    router.put("/api/projects/{id}/archive", archive_project)
    router.post("/api/projects/{id}/milestones/{mid}/bump", bump_ms)
    router.delete("/api/projects/{id}", del_project)
    router.get("/api/projects/{id}/items", items)
    router.post("/api/projects/{id}/items", add_item)
    router.put("/api/items/{id}", upd_item)
    router.delete("/api/items/{id}", del_item)
    router.get("/api/resumes", resumes)

    # ================= 面试 =================
    I = lambda: ctx.services.get("interview_service")

    def schedules(ctx: AppContext, params, body, query):
        return {"items": I().schedules()}

    def add_schedule(ctx: AppContext, params, body, query):
        if not body.get("meet_at") or not body.get("company"):
            return 400, {"error": "meet_at/company 必填"}
        sid = I().add_schedule(body["meet_at"], body["company"],
                               body.get("round", ""), body.get("note", ""))
        return 201, {"id": sid}

    def del_schedule(ctx: AppContext, params, body, query):
        I().delete_schedule(int(params["id"]))
        return {"ok": True}

    def reviews(ctx: AppContext, params, body, query):
        return {"items": I().reviews()}

    def add_review(ctx: AppContext, params, body, query):
        rid = I().add_review(body.get("date") or __import__("datetime").date.today().isoformat(),
                             body["company"], body.get("round", ""), body.get("questions", ""),
                             body.get("performance", ""), body.get("improve", ""))
        return 201, {"id": rid}

    def del_review(ctx: AppContext, params, body, query):
        I().delete_review(int(params["id"]))
        return {"ok": True}

    def offers(ctx: AppContext, params, body, query):
        return {"items": I().offers()}

    def add_offer(ctx: AppContext, params, body, query):
        oid = I().add_offer(body["company"], body.get("salary", ""), body.get("location", ""),
                            body.get("direction", ""), body.get("growth", ""),
                            int(body.get("score", 3)), body.get("note", ""))
        return 201, {"id": oid}

    def del_offer(ctx: AppContext, params, body, query):
        I().delete_offer(int(params["id"]))
        return {"ok": True}

    router.get("/api/interviews", schedules)
    router.post("/api/interviews", add_schedule)
    router.delete("/api/interviews/{id}", del_schedule)
    router.get("/api/interview-reviews", reviews)
    router.post("/api/interview-reviews", add_review)
    router.delete("/api/interview-reviews/{id}", del_review)
    router.get("/api/offers", offers)
    router.post("/api/offers", add_offer)
    router.delete("/api/offers/{id}", del_offer)

    # ================= 雅思 =================
    E = lambda: ctx.services.get("ielts_service")

    def ielts_cfg(ctx: AppContext, params, body, query):
        cfg = E().config()
        cfg["days_left"] = E().days_left()
        return cfg

    def ielts_set_cfg(ctx: AppContext, params, body, query):
        return E().set_config(body)

    def ielts_tests(ctx: AppContext, params, body, query):
        return {"items": E().tests(), "trend": E().trend()}

    def ielts_add_test(ctx: AppContext, params, body, query):
        tid = E().add_test(body.get("date"), body.get("book", ""), body.get("test_no", ""),
                           body.get("listening"), body.get("reading"),
                           body.get("writing"), body.get("speaking"), body.get("note", ""))
        return 201, {"id": tid}

    def ielts_mistakes(ctx: AppContext, params, body, query):
        return {"items": E().mistakes(), "stats": E().mistake_stats()}

    def ielts_add_mistake(ctx: AppContext, params, body, query):
        mid = E().add_mistake(body.get("date"), body["subject"], body["qtype"],
                              body.get("reason", ""), body.get("ref", ""))
        return 201, {"id": mid}

    def ielts_topics(ctx: AppContext, params, body, query):
        return {"items": E().topics()}

    def ielts_add_topic(ctx: AppContext, params, body, query):
        tid = E().add_topic(int(body.get("part", 2)), body["topic"], int(body.get("freq", 0)))
        return 201, {"id": tid}

    def ielts_toggle_topic(ctx: AppContext, params, body, query):
        E().toggle_practiced(int(params["id"]))
        return {"ok": True}

    def ielts_del_topic(ctx: AppContext, params, body, query):
        E().delete_topic(int(params["id"]))
        return {"ok": True}

    def ielts_del_mistake(ctx: AppContext, params, body, query):
        E().delete_mistake(int(params["id"]))    # v1.19
        return {"ok": True}

    def ielts_del_bank(ctx: AppContext, params, body, query):
        try:
            return E().delete_bank_set(params["id"])   # v1.19：仅本机文件题组可删
        except ValueError as e:
            return 400, {"error": str(e)}

    def ielts_writings(ctx: AppContext, params, body, query):
        return {"items": E().writings()}

    def ielts_add_writing(ctx: AppContext, params, body, query):
        wid = E().add_writing(body.get("date"), body["topic"], body.get("content", ""))
        return 201, {"id": wid}

    def ielts_mocks(ctx: AppContext, params, body, query):
        return {"items": E().mocks()}

    def ielts_add_mock(ctx: AppContext, params, body, query):
        mid = E().add_mock(body["date"], body.get("kind", "full"), body.get("note", ""))
        return 201, {"id": mid}

    def ielts_del_mock(ctx: AppContext, params, body, query):
        E().delete_mock(int(params["id"]))
        return {"ok": True}

    # ---- 刷题题库（F17/F18） ----
    def ielts_bank(ctx: AppContext, params, body, query):
        return {"items": E().bank_list(query.get("subject"))}

    def ielts_bank_import(ctx: AppContext, params, body, query):
        return E().bank_import(body)

    def ielts_bank_set(ctx: AppContext, params, body, query):
        s = E().bank_get(params["id"])
        return s or (404, {"error": "题组不存在"})

    def ielts_audio(ctx: AppContext, params, body, query):
        """F26：返回本机音频文件（传输层特判 _audio_file 发二进制）；无则 404，前端降级 TTS。"""
        import mimetypes
        p = E().audio_file(params["set_id"], params["sec"])
        if not p:
            return 404, {"error": "本机无此节音频"}
        return 200, {"_audio_file": str(p),
                     "_audio_type": mimetypes.guess_type(p.name)[0] or "audio/mpeg"}

    def ielts_news_fetch(ctx: AppContext, params, body, query):
        """v1.14：拉取 BBC/VOA 最新文章，纯脚本生成题组（不用 AI）。"""
        return E().news_fetch(body.get("kind") or "reading",
                              body.get("source") or "auto",
                              body.get("count") or 1)

    def ielts_speak_bank(ctx: AppContext, params, body, query):
        """v1.15：口语话题库（seed+自建合并，part 可选）。"""
        part = query.get("part")
        return {"items": E().speak_bank(int(part) if part else None)}

    def ielts_speak_daily(ctx: AppContext, params, body, query):
        """v1.15：今日话题（Part 2 池按日期轮换）。"""
        return E().speak_daily()

    def ielts_speak_note(ctx: AppContext, params, body, query):
        """v1.15：保存"我的版本"。"""
        return E().speak_note(body.get("seed_id") or "", body.get("text"))

    def ielts_rec_list(ctx: AppContext, params, body, query):
        """v1.16：某话题的录音列表。"""
        return E().rec_list(params["key"])

    def ielts_rec_save(ctx: AppContext, params, body, query):
        """v1.16：上传录音（server 层已把 audio/* 转为 body['_raw_bytes']）。"""
        return E().rec_save(params["key"],
                            (body.get("_ctype") or "") if isinstance(body, dict) else "",
                            body.get("_raw_bytes") if isinstance(body, dict) else None)

    def ielts_rec_file(ctx: AppContext, params, body, query):
        """v1.16：回放某条录音（传输层 _audio_file 二进制直出）。"""
        import mimetypes
        got = E().rec_file(params["key"], params["name"])
        if not got:
            return 404, {"error": "录音不存在"}
        mime, p = got
        return 200, {"_audio_file": str(p), "_audio_type": mime}

    def ielts_rec_delete(ctx: AppContext, params, body, query):
        return E().rec_delete(params["key"], params["name"])

    def ielts_write_bank(ctx: AppContext, params, body, query):
        """v1.16：写作题库（task 可选 1/2）。"""
        task = query.get("task")
        return E().write_bank(int(task) if task else None)

    def ielts_write_daily(ctx: AppContext, params, body, query):
        """v1.16：今日写作任务（T1/T2 各一）。"""
        return E().write_daily()

    def ielts_write_note(ctx: AppContext, params, body, query):
        """v1.16：保存"我的作文"。"""
        return E().write_note(body.get("seed_id") or "", body.get("text"))

    def ielts_bank_submit(ctx: AppContext, params, body, query):
        r = E().bank_submit(params["id"], body.get("answers") or {})
        return r or (404, {"error": "题组不存在"})

    def ielts_attempts(ctx: AppContext, params, body, query):
        return E().attempt_stats()

    router.get("/api/ielts/config", ielts_cfg)
    router.put("/api/ielts/config", ielts_set_cfg)
    router.get("/api/ielts/tests", ielts_tests)
    router.post("/api/ielts/tests", ielts_add_test)
    router.get("/api/ielts/mistakes", ielts_mistakes)
    router.post("/api/ielts/mistakes", ielts_add_mistake)
    router.get("/api/ielts/topics", ielts_topics)
    router.post("/api/ielts/topics", ielts_add_topic)
    router.post("/api/ielts/topics/{id}/toggle", ielts_toggle_topic)
    router.delete("/api/ielts/topics/{id}", ielts_del_topic)
    router.delete("/api/ielts/mistakes/{id}", ielts_del_mistake)   # v1.19
    router.delete("/api/ielts/bank/{id}", ielts_del_bank)          # v1.19
    router.get("/api/ielts/writings", ielts_writings)
    router.post("/api/ielts/writings", ielts_add_writing)
    router.get("/api/ielts/mocks", ielts_mocks)
    router.post("/api/ielts/mocks", ielts_add_mock)
    router.delete("/api/ielts/mocks/{id}", ielts_del_mock)
    router.get("/api/ielts/bank", ielts_bank)
    router.post("/api/ielts/bank/import", ielts_bank_import)   # 字面量须先于 {id}
    router.get("/api/ielts/bank/{id}", ielts_bank_set)
    router.get("/api/ielts/audio/{set_id}/{sec}", ielts_audio)
    router.post("/api/ielts/news/fetch", ielts_news_fetch)
    router.get("/api/ielts/speak/bank", ielts_speak_bank)
    router.get("/api/ielts/speak/daily", ielts_speak_daily)
    router.post("/api/ielts/speak/note", ielts_speak_note)
    router.get("/api/ielts/speak/recording/{key}", ielts_rec_list)
    router.post("/api/ielts/speak/recording/{key}", ielts_rec_save)
    router.get("/api/ielts/speak/recording/{key}/{name}", ielts_rec_file)
    router.delete("/api/ielts/speak/recording/{key}/{name}", ielts_rec_delete)
    router.get("/api/ielts/write/bank", ielts_write_bank)
    router.get("/api/ielts/write/daily", ielts_write_daily)
    router.post("/api/ielts/write/note", ielts_write_note)
    router.post("/api/ielts/bank/{id}/submit", ielts_bank_submit)
    router.get("/api/ielts/attempts", ielts_attempts)

    # ================= 力扣 =================
    L = lambda: ctx.services.get("leetcode_service")

    def lc_sync(ctx: AppContext, params, body, query):
        return L().sync()

    def lc_cache(ctx: AppContext, params, body, query):
        return {"configured": L().configured(), "cache": L().cached()}

    def lc_folder(ctx: AppContext, params, body, query):
        return L().folder_status()

    def lc_ask(ctx: AppContext, params, body, query):
        if not (body or {}).get("question", "").strip():
            return 400, {"error": "问题不能为空"}
        return L().ask(body["question"])

    def lc_review_pick(ctx: AppContext, params, body, query):
        try:
            return L().review_pick((body or {}).get("n", 5))
        except ValueError as e:
            return 400, {"error": str(e)}

    def lc_review_grade(ctx: AppContext, params, body, query):
        b = body or {}
        if not b.get("question", "").strip() or not b.get("answer", "").strip():
            return 400, {"error": "题目与作答不能为空"}
        return L().review_grade(b["question"], b["answer"], b.get("ref", ""))

    def lc_review_mark(ctx: AppContext, params, body, query):
        b = body or {}
        try:
            return L().review_mark(b.get("id", ""), b.get("result", ""))
        except ValueError as e:
            return 400, {"error": str(e)}

    router.post("/api/leetcode/sync", lc_sync)
    router.get("/api/leetcode/status", lc_cache)
    router.get("/api/leetcode/folder", lc_folder)
    router.post("/api/leetcode/ask", lc_ask)
    router.post("/api/leetcode/review/pick", lc_review_pick)
    router.post("/api/leetcode/review/grade", lc_review_grade)
    router.post("/api/leetcode/review/mark", lc_review_mark)
