# -*- coding: utf-8 -*-
"""事件总线：模块间异步解耦的唯一通知通道。

规则（见 docs/ARCHITECTURE.md §5）：
- 发布方只管发布，不关心谁在听；
- 订阅方异常不影响其他订阅方，也不影响发布方。
"""
import logging

LOG = logging.getLogger("workbench.events")


class EventBus:
    def __init__(self):
        self._subs: dict[str, list] = {}

    def subscribe(self, topic: str, handler):
        """handler(payload: dict) -> None"""
        self._subs.setdefault(topic, []).append(handler)

    def publish(self, topic: str, payload: dict | None = None):
        for handler in list(self._subs.get(topic, [])):
            try:
                handler(payload or {})
            except Exception:
                LOG.exception("事件处理失败 topic=%s handler=%s", topic, getattr(handler, "__name__", handler))

    def topics(self) -> list[str]:
        return sorted(self._subs)
