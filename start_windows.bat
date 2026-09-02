@echo off
chcp 65001 >nul
title OpenHaptic-Roleplay // Windows Native Launcher
color 0b

echo =====================================================================
echo    🚀 OpenHaptic-Roleplay [Windows 原生免 Docker 极速版]
echo    ⚡ AMD Radeon 780M DirectML 硬件加速 + YOLO11-Pose + ESP32-C3
echo =====================================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+ 并勾选 "Add to PATH"。
    pause
    exit /b
)

:: 检查并自动创建 models 目录
if not exist "modelsyolo11n-pose.onnx" (
    echo [*] 正在初始化并导出 YOLO11s-Pose (640高清 FP16 模型)...
    python toolsexport_yolo11_hw.py --model yolo11s-pose.pt --imgsz 640
)

echo [*] 启动主控服务...
echo 👉 PC 控制台: http://localhost:8000
echo 👉 手机推流端: http://127.0.0.1:8000/phone (在 iPhone 上将 127.0.0.1 换为你电脑的局域网 IP)
echo.

python main.py --driver esp32 --camera phone --web-port 8000

pause
