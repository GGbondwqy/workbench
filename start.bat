@echo off
chcp 65001 >nul
cd /d %~dp0
where python >nul 2>nul
if errorlevel 1 (
  echo [学途工作台] 未找到 python，请先安装 Python 3.10+ 并加入 PATH。
  pause
  exit /b 1
)
python server.py
pause
