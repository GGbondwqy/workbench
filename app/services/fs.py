# -*- coding: utf-8 -*-
"""本地文件夹浏览设施（v2.5 / F25）：给前端"浏览…"导航小窗提供目录列表。

约束：只列目录名，不读任何文件内容；本地单机工具，无跨机暴露面。
"""
import ctypes
import os
from pathlib import Path

from app.core.registry import AppContext

MIGRATIONS = []


def _windows_drives():
    buf = ctypes.create_unicode_buffer(512)
    n = ctypes.windll.kernel32.GetLogicalDriveStringsW(512, buf)
    raw = ctypes.wstring_at(buf, n)  # 形如 "C:\\\0D:\\"
    return [d.rstrip("\\") for d in raw.split("\0") if d]


class FsService:
    name = "fs_service"

    def __init__(self, ctx: AppContext):
        self._ctx = ctx

    def folders(self, path=""):
        """path 空 → 磁盘根（盘符/根目录）；否则列子文件夹（仅目录）。"""
        if not path:
            if os.name == "nt":
                items = [{"name": f"{d} 盘", "path": f"{d}\\"} for d in _windows_drives()]
            else:
                items = [{"name": "/", "path": "/"}]
            return {"path": "", "parent": "", "folders": items}
        if len(path) == 2 and path[1] == ":":
            path += "\\"  # 裸盘符 "D:" 是"盘上当前目录"而非盘根，统一归一到 "D:\"
        p = Path(path)
        if not p.is_dir():
            return {"error": f"路径不存在或不是文件夹：{path}"}
        try:
            entries = sorted(p.iterdir(), key=lambda x: x.name.lower())
        except PermissionError:
            return {"error": f"无权访问：{path}"}
        folders = []
        for e in entries:
            try:
                if e.is_dir():
                    folders.append({"name": e.name, "path": str(e)})
            except OSError:
                continue
        parent = str(p.parent)
        return {"path": str(p), "parent": "" if parent == str(p) else parent,
                "folders": folders}


def register(ctx: AppContext):
    ctx.services.register(FsService.name, FsService(ctx))
