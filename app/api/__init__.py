# -*- coding: utf-8 -*-
"""API 层：薄路由。只做 参数解析 → 调 service → 返回 JSON，禁止直接访问 db。

约定：路由模块命名 routes_*.py，暴露 register_routes(router, ctx)，
bootstrap 自动扫描（见 docs/ARCHITECTURE.md §4）。
"""
import re


class ApiRouter:
    def __init__(self):
        # [(method, pattern_parts, handler)]
        self._routes: list[tuple[str, list[str], object]] = []

    def add(self, method: str, path: str, handler):
        parts = [p for p in path.strip("/").split("/")]
        self._routes.append((method.upper(), parts, handler))

    def get(self, path, handler):
        self.add("GET", path, handler)

    def post(self, path, handler):
        self.add("POST", path, handler)

    def put(self, path, handler):
        self.add("PUT", path, handler)

    def delete(self, path, handler):
        self.add("DELETE", path, handler)

    def dispatch(self, method: str, path: str, ctx, body: dict, query: dict):
        """返回 (status, obj)；无匹配返回 None。handler 返回 dict 视为 200。"""
        req_parts = [p for p in path.strip("/").split("/")]
        for m, parts, handler in self._routes:
            if m != method.upper() or len(parts) != len(req_parts):
                continue
            params = {}
            matched = True
            for pat, req in zip(parts, req_parts):
                if pat.startswith("{") and pat.endswith("}"):
                    params[pat[1:-1]] = req
                elif pat != req:
                    matched = False
                    break
            if not matched:
                continue
            result = handler(ctx, params, body, query)
            if isinstance(result, tuple):
                return result
            return 200, result
        return None
