# -*- coding: utf-8 -*-
"""组装点（Composition Root）：自动发现 services 与 api 路由，执行迁移。

新增业务模块零改动（见 docs/ARCHITECTURE.md §4）：
services/xxx.py 暴露 register(ctx) [+ MIGRATIONS]；api/routes_xxx.py 暴露 register_routes。
"""
import importlib
import logging
import pkgutil
import sys
from pathlib import Path

from app import ai as ai_pkg
from app import api as api_pkg
from app import services as services_pkg
from app.core import config as config_mod
from app.core.db import Database
from app.core.events import EventBus
from app.core.registry import AppContext

LOG = logging.getLogger("workbench.bootstrap")


def _setup_logging(data_dir: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(fmt)
        root.addHandler(stream)
    file_h = logging.FileHandler(data_dir / "workbench.log", encoding="utf-8")
    file_h.setFormatter(fmt)
    root.addHandler(file_h)


def create_app(root: Path):
    data_dir = root / "data"
    _setup_logging(data_dir)

    cfg = config_mod.load_config(data_dir)
    db = Database(data_dir / "workbench.db")
    events = EventBus()
    ctx = AppContext(root=root, data_dir=data_dir, config=cfg,
                     db=db, events=events,
                     ai=ai_pkg.AIRegistry(cfg.get("ai", {})))

    # 1) 自动发现服务模块：register(ctx) 注册服务；MIGRATIONS 登记建表
    modules = []
    migrations = []
    for mod in pkgutil.iter_modules(services_pkg.__path__):
        if mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"{services_pkg.__name__}.{mod.name}")
        modules.append(module)
        migrations.extend(getattr(module, "MIGRATIONS", []))
        register = getattr(module, "register", None)
        if register:
            register(ctx)
    db.migrate(migrations)

    # 2) 迁移完成后回调：各模块可在此做种子数据等需要查表的初始化
    for module in modules:
        post = getattr(module, "post_migrate", None)
        if post:
            post(ctx)

    # 3) 自动发现路由模块
    router = api_pkg.ApiRouter()
    for mod in pkgutil.iter_modules(api_pkg.__path__):
        if not mod.name.startswith("routes_"):
            continue
        module = importlib.import_module(f"{api_pkg.__name__}.{mod.name}")
        register_routes = getattr(module, "register_routes", None)
        if register_routes:
            register_routes(router, ctx)

    LOG.info("应用组装完成 services=%s migrations=%d", ctx.services.names(), len(migrations))
    return ctx, router
