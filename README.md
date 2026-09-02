# ⚡ OpenHaptic-Roleplay (YoloHaptic)

> 🎮 **下一代多模态 AI 具身角色扮演与触觉体感交互框架**
> 
> *A Next-Gen Multimodal Vision-Driven Haptic & Interactive Roleplay Framework powered by YOLO11, ESP32, Sensor Fusion & Multi-Device HAL.*

[English Documentation](README_EN.md) | [安全免责声明](DISCLAIMER.md) | [贡献指南](CONTRIBUTING.md)

---

## 🌟 核心亮点 (Key Highlights)

- 👁️ **毫秒级视觉反馈 (<30ms)**：基于 **YOLO11-Pose** 实时检测人体骨骼、敏感弱点防护姿态与挣扎剧烈度指数。
- 🧭 **视觉 + 陀螺仪多模态感知 (Sensor Fusion)**：融合 YOLO 骨骼点与 iPhone/ESP32 陀螺仪加速度，精准捕捉高频生理抽搐/痉挛与倒地扑街状态。
- ⚡ **多设备全生态驱动 (Unified HAL)**：
  - **ESP32-C3 SuperMini / S3**：原生 USB-CDC 通信、4路 PWM、平滑波形生成、**2000ms 硬件级急停看门狗**。
  - **役次元 (YOKONEX)**：支持腾讯云 IM 远程联动、蓝牙直连与全系玩具生态。
  - **郊狼 (DG-LAB)**：双通道电击波形调控、实时 A/B 通道强度回传、**贴片脱落断开报警**。
- 🧠 **双循环具身智能体 (Hybrid Brain)**：
  - **⚡ 快循环 (Fast-Loop)**：视觉事件瞬间触发物理打击或波形收束。
  - **🧠 慢循环 (Slow-Loop)**：本地大模型 (Ollama Qwen2.5 / DeepSeek) 结合真实硬件读数生成沉浸剧本，并由 **Kokoro TTS** 真人级声线实时配音。
- 💻 **全平台硬件加速 (零 NVIDIA 绑定)**：完美适配 **AMD Radeon 780M / Intel 核显 / Apple Silicon / NVIDIA GPU** (基于 DirectML / OpenVINO / ONNXRuntime)。
- 📱 **赛博朋克 Web 控制台 & 手机无线推流**：PC 端实时查看能量条、姿态准星与急停按钮；手机 Safari 扫码一键无线图传与陀螺仪上送。

---

## 📂 项目架构

```text
OpenHaptic-Roleplay/
├── firmware/esp32-c3-supermini/ # ESP32-C3 SuperMini 通用固件 (PlatformIO)
├── src/
│   ├── drivers/                 # 统一硬件抽象层 (ESP32 / 役次元 / 郊狼)
│   ├── vision/                  # YOLO11-Pose 视觉引擎
│   ├── core/                    # 快慢决策循环、传感器融合、Kokoro TTS 语音引擎
│   └── ui/                      # FastAPI + WebSocket 赛博朋克控制台 & 手机端
├── config/scenarios/            # 剧本配置文件 (如: 触手战败屋)
├── tools/                       # YOLO11 FP16 硬件加速一键导出工具
├── start_windows.bat            # Windows 本地一键启动脚本
└── requirements-amd.txt         # Windows / AMD / DirectML 依赖清单
```

---

## 🚀 极速上手 (Quick Start)

### 1. 硬件准备与固件烧录 (可选 ESP32-C3 SuperMini)
1. 用 VS Code 安装 **PlatformIO IDE** 插件并打开 `firmware/esp32-c3-supermini` 目录。
2. 用 Type-C 线连接开发板，点击底部工具栏 **Upload** 烧录。
   - `GPIO0`：PWM 输出通道 0（接马达驱动/信号输入）
   - `GPIO8`：板载蓝色状态 LED 指示灯
   - `GPIO4 / GPIO5`：可选接 MPU6050 陀螺仪 (I2C)

---

### 2. Windows 本地极速运行 (免 Docker)

1. **克隆项目并安装依赖**：
   ```powershell
   git clone https://github.com/你的用户名/OpenHaptic-Roleplay.git
   cd OpenHaptic-Roleplay
   pip install -r requirements-amd.txt
   ```

2. **下载真人级 Kokoro TTS 模型 (约 82MB)**：
   ```powershell
   mkdir -p models\tts\kokoro
   curl -L -o models\tts\kokoro\kokoro-v0.19.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0.19-int8.onnx
   curl -L -o models\tts\kokoro\voices.json https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices-v0.19.json
   ```

3. **双击运行**：
   直接双击 **`start_windows.bat`**（或命令行输入 `python main.py --driver esp32 --camera phone`）。
   - **PC 控制台**：浏览器打开 `http://localhost:8000`
   - **手机推流端**：iPhone Safari 访问 `http://你的电脑局域网IP:8000/phone` 并点击“开始推流”

---

## 🛡️ 安全与急停机制

- **全局急停快捷键**：在 PC 网页控制台中随时按 **`空格键 (SPACE)`**，立即切断所有硬件通道输出。
- **固件看门狗 (Safety Watchdog)**：ESP32 连续 2000ms 未收到上位机心跳包时，硬件层面立即自动切断所有输出（Fail-Safe）。
- **贴片脱落保护**：郊狼等电击设备检测到电极开路脱落时，驱动层立即暂停输出并报警。

---

## 🤝 贡献与生态接入

欢迎提交 PR 适配更多硬件与玩法！
- 查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何编写新设备驱动或贡献新剧本。
- 提交 [Issue](https://github.com/你的用户名/OpenHaptic-Roleplay/issues) 提出新功能建议。

---

## 📄 开源许可证

本项目基于 [GPLv3 许可证](LICENSE) 开源。仅供个人学习、科研与非商业化使用。
