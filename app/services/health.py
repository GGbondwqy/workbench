# -*- coding: utf-8 -*-
"""健康检查服务（示范模块：register 模式 + 无表服务）。"""
import time

from app.core.registry import AppContext
from app.core.timeutil import now_iso


class HealthService:
    name = "health_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx
        self.started_at = now_iso()

    def snapshot(self) -> dict:
        return {
            "status": "ok",
            "app": self._ctx.config["app"]["name"],
            "version": self._ctx.config["app"]["version"],
            "started_at": self.started_at,
            "uptime_sec": int(time.time() - time.mktime(time.strptime(self.started_at, "%Y-%m-%dT%H:%M:%S"))),
        }


def register(ctx: AppContext):
    ctx.services.register(HealthService.name, HealthService(ctx))
