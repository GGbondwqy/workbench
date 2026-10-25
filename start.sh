#!/usr/bin/env bash
# 学途工作台启动脚本（Linux / macOS）
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[学途工作台] 未找到 python3，请先安装 Python 3.10+"
  exit 1
fi
exec python3 server.py "$@"
