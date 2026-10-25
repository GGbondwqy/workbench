# -*- coding: utf-8 -*-
"""业务逻辑层：每个业务域一个模块。

约定（见 docs/ARCHITECTURE.md §4）：
- 模块可暴露 MIGRATIONS = [(id, sql), ...] 声明自己的表（只建/只写自己域的表）
- 暴露 register(ctx) 完成服务注册与事件订阅
- 禁止 import 其他 service 模块；跨域走 ctx.services / ctx.events
- bootstrap 会自动扫描本目录，新增模块无需改任何现有文件
"""
