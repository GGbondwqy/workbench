# -*- coding: utf-8 -*-
"""配置管理：内置默认值 + data/config.json 本地覆盖（该文件 gitignore，可存私钥）。"""
import copy
import json
import logging
from pathlib import Path

LOG = logging.getLogger("workbench.config")

DEFAULTS = {
    "app": {"name": "学途工作台", "version": "0.1.0"},
    "server": {"host": "127.0.0.1", "port": 8787},
    # AI 多档案配置：OpenAI 兼容格式，base_url + api_key + model。
    # active 为 null 时全部降级为本地规则引擎；预置三个档案模板，key 留空。
    "ai": {
        "active": None,
        "providers": [
            {"name": "deepseek", "base_url": "https://api.deepseek.com/v1",
             "api_key": "", "model": "deepseek-chat", "enabled": True},
            {"name": "qwen", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
             "api_key": "", "model": "qwen-plus", "enabled": True},
            {"name": "relay", "base_url": "", "api_key": "", "model": "", "enabled": False},
        ],
    },
    # 知识库挂载路径（小林八股等 Markdown 库），指向仓库外目录
    "kb": {"path": None},
}


def _deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(data_dir: Path) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    user_file = data_dir / "config.json"
    if user_file.is_file():
        try:
            user = json.loads(user_file.read_text(encoding="utf-8"))
            _deep_merge(cfg, user)
        except (ValueError, OSError) as e:
            LOG.warning("config.json 解析失败，使用默认配置: %s", e)
    return cfg


def save_config(data_dir: Path, cfg: dict):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
