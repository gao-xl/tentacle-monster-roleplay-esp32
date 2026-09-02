@echo off
chcp 65001 >nul
title OpenHaptic-Roleplay Launcher

echo =======================================================
echo    🚀 OpenHaptic-Roleplay 一键启动器
echo =======================================================
echo.

python main.py --driver esp32 --camera 0 --web-port 8000

pause
