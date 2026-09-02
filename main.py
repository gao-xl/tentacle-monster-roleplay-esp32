"""
OpenHaptic-Roleplay Master Unified Runner
Integrates:
- Hardware HAL (ESP32-C3 SuperMini, Yokonex, DG-LAB)
- YOLO-Pose Vision Engine
- Gyroscope / IMU Sensor Fusion
- Fast-Loop Physical Feedback (<30ms)
- Slow-Loop LLM AI Narrative Engine + Voice TTS
- FastAPI Cyberpunk Web Dashboard & Phone Wireless Streamer
"""

import os
import sys
import time
import argparse
import logging
import threading
import cv2
import uvicorn

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.drivers.base import BaseDeviceDriver
from src.drivers.esp32_driver import ESP32Driver
from src.drivers.yokonex_driver import YokonexDriver
from src.drivers.dglab_driver import DGLabDriver
from src.vision.yolo_tracker import YOLOPoseTracker
from src.core.sensor_fusion import SensorFusionEngine
from src.core.fast_loop import FastLoopEngine
from src.core.slow_loop import SlowLoopEngine
from src.core.tts_engine import TTSEngine
from src.ui.web_server import app, shared_state, broadcast_ai_dialogue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("OpenHaptic-Master")


def main():
    parser = argparse.ArgumentParser(description="OpenHaptic-Roleplay Unified AI Haptic Framework")
    parser.add_argument("--driver", choices=["esp32", "yokonex", "dglab", "virtual"], default="esp32", help="Target hardware driver")
    parser.add_argument("--port", default=None, help="ESP32 Serial COM port")
    parser.add_argument("--camera", default="0", help="Camera source (0 for USB webcam, or 'phone' for iPhone wireless stream)")
    parser.add_argument("--max-power", type=float, default=70.0, help="Safety maximum power limit %")
    parser.add_argument("--llm-key", default=None, help="DeepSeek or OpenAI API Key for AI narration")
    parser.add_argument("--web-port", type=int, default=8000, help="Web Dashboard Port")
    args = parser.parse_args()

    print("=" * 70)
    print("  🚀 OPENHAPTIC-ROLEPLAY // NEXT-GEN AI HAPTIC SYSTEM ONLINE  ")
    print("=" * 70)

    # 1. Initialize Hardware Driver
    driver: BaseDeviceDriver
    if args.driver == "esp32":
        logger.info("[1/5] Connecting to ESP32-C3 SuperMini...")
        driver = ESP32Driver(port=args.port)
    elif args.driver == "yokonex":
        logger.info("[1/5] Connecting to YOKONEX API-bridge...")
        driver = YokonexDriver()
    elif args.driver == "dglab":
        logger.info("[1/5] Connecting to DG-LAB Coyote...")
        driver = DGLabDriver()
    else:
        logger.info("[1/5] Using Virtual Driver...")
        from src.drivers.base import BaseDeviceDriver, DeviceTelemetry, DeviceType
        class VirtualDriver(BaseDeviceDriver):
            def connect(self): return True
            def disconnect(self): pass
            def vibrate(self, *a, **k): return True
            def hit(self, *a, **k): return True
            def wave(self, *a, **k): return True
            def shock(self, *a, **k): return True
            def stop_all(self): return True
            def get_telemetry(self): return DeviceTelemetry("Virtual", DeviceType.VIRTUAL, True)
        driver = VirtualDriver()

    driver.connect()
    shared_state["driver"] = driver

    # 2. Initialize Vision & Sensor Fusion
    logger.info("[2/5] Loading YOLO-Pose Vision Engine...")
    tracker = YOLOPoseTracker()
    fusion_engine = SensorFusionEngine()

    # 3. Initialize Decision & AI Narrative Engine
    logger.info("[3/5] Initializing Fast-Loop & Slow-Loop Brains...")
    fast_loop = FastLoopEngine(driver=driver, max_power_limit=args.max_power)
    slow_loop = SlowLoopEngine(api_key=args.llm_key)
    tts_engine = TTSEngine()

    def on_ai_line(line: str):
        tts_engine.speak_async(line, on_complete=lambda url: broadcast_ai_dialogue(line, url))

    slow_loop.on_narrative_generated = on_ai_line

    # 4. Start Web Dashboard Background Server
    logger.info(f"[4/5] Starting Web Dashboard on http://localhost:{args.web_port}...")
    def run_web():
        uvicorn.run(app, host="0.0.0.0", port=args.web_port, log_level="warning")

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    # 5. Open Camera Input
    is_phone_cam = (args.camera.lower() == "phone")
    cap = None
    if not is_phone_cam:
        cam_idx = int(args.camera) if args.camera.isdigit() else args.camera
        cap = cv2.VideoCapture(cam_idx)

    logger.info("[5/5] All Subsystems Active! Ready for Roleplay.")
    print(f"
👉 PC 控制台面板: http://localhost:{args.web_port}")
    print(f"👉 手机端推流地址: http://[你的局域网IP]:{args.web_port}/phone
")

    try:
        while True:
            # Grab Frame
            frame = None
            if is_phone_cam:
                frame = shared_state.get("current_frame")
            elif cap and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.04)
                    continue

            if frame is None:
                time.sleep(0.04)
                continue

            # A. YOLO Vision Processing
            pose_result, annotated = tracker.process_frame(frame)
            shared_state["annotated_frame"] = annotated

            # B. Gyro / Sensor Fusion
            phone_imu = shared_state.get("phone_imu")
            fused_state = fusion_engine.fuse(pose_result, phone_imu)
            shared_state["fused_state"] = fused_state

            # C. Telemetry Update
            telemetry = driver.get_telemetry()
            shared_state["device_telemetry"] = telemetry

            # D. Fast-Loop Physical Feedback (<30ms)
            fast_loop.update(pose_result)

            # E. Slow-Loop AI Narrative & Story State
            slow_loop.tick(fused_state, telemetry)

            time.sleep(0.02)  # ~50 FPS loop

    except KeyboardInterrupt:
        print("
Shutdown requested by user...")
    finally:
        logger.info("Releasing hardware and resources...")
        driver.stop_all()
        driver.disconnect()
        if cap:
            cap.release()
        logger.info("System safely offline.")


if __name__ == "__main__":
    main()
