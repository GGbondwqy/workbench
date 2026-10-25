# -*- coding: utf-8 -*-
"""服务注册表与应用上下文：业务模块间协作的合法入口（禁止相互 import）。"""
from dataclasses import dataclass, field
from pathlib import Path


class ServiceRegistry:
    def __init__(self):
        self._services: dict[str, object] = {}

    def register(self, name: str, instance):
        if name in self._services:
            raise ValueError(f"服务重复注册: {name}")
        self._services[name] = instance

    def get(self, name: str):
        """未注册时抛 KeyError——组装期就该暴露问题。"""
        return self._services[name]

    def try_get(self, name: str):
        return self._services.get(name)

    def names(self) -> list[str]:
        return sorted(self._services)


@dataclass
class AppContext:
    """贯穿各层的上下文，由 bootstrap 组装后传入。"""
    root: Path = None          # 项目根目录
    data_dir: Path = None
    config: dict = field(default_factory=dict)
    db: object = None
    events: object = None
    services: ServiceRegistry = field(default_factory=ServiceRegistry)
    ai: object = None

    def close(self):
        if self.db is not None:
            self.db.close()
