"""
OpenHaptic-Roleplay v0.1 Entry Point
Runs real-time camera capture, YOLO-Pose tracking, HUD overlay, and ESP32-C3 SuperMini physical feedback.
"""

import sys
import os
import argparse
import time
import logging
import cv2

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.drivers.esp32_driver import ESP32Driver
from src.vision.yolo_tracker import YOLOPoseTracker
from src.core.fast_loop import FastLoopEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("OpenHaptic-v0.1")


def main():
    parser = argparse.ArgumentParser(description="OpenHaptic-Roleplay v0.1 Runtime")
    parser.add_argument("--camera", default="0", help="Camera index (0, 1...) or RTSP/HTTP stream URL")
    parser.add_argument("--port", default=None, help="ESP32 Serial COM port (e.g. COM3 or /dev/ttyACM0). Auto-detected if omitted.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--max-power", type=float, default=70.0, help="Safety power limit in % (default: 70)")
    parser.add_argument("--model", default="yolov8n-pose.pt", help="YOLO Pose model file")
    args = parser.parse_args()

    print("=" * 65)
    print("  🚀 OpenHaptic-Roleplay v0.1 (YOLO Vision + ESP32-C3 SuperMini)  ")
    print("=" * 65)

    # 1. Initialize Hardware Driver
    print("[1/3] Initializing ESP32-C3 Controller...")
    driver = ESP32Driver(port=args.port, baudrate=args.baud)
    connected = driver.connect()
    if not connected:
        print("[WARN] ESP32 not detected. Running in VIRTUAL/PREVIEW mode (Vision only).")
    else:
        print("[OK] ESP32 Connected successfully with Active Watchdog!")

    # 2. Initialize Vision Engine
    print(f"[2/3] Loading YOLO Vision Engine ({args.model})...")
    tracker = YOLOPoseTracker(model_name=args.model)

    # 3. Initialize Decision Engine
    print("[3/3] Initializing Fast Loop Event Engine...")
    engine = FastLoopEngine(driver=driver, max_power_limit=args.max_power)

    # Open Camera
    cam_src = int(args.camera) if args.camera.isdigit() else args.camera
    cap = cv2.VideoCapture(cam_src)
    if not cap.isOpened():
        logger.error(f"Cannot open camera source: {args.camera}")
        driver.disconnect()
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("
[READY] System Running! Controls:")
    print("  - [q]       : Exit program")
    print("  - [SPACE]   : Emergency Stop (zero all channels)")
    print("  - [h]       : Test manual HIT on ESP32")
    print("-" * 65)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to grab camera frame. Retrying...")
                time.sleep(0.05)
                continue

            # Process YOLO Vision
            pose_result, annotated_frame = tracker.process_frame(frame)

            # Process Decision & Hardware Feedback
            if connected:
                engine.update(pose_result)

            # Display Window
            cv2.imshow("OpenHaptic-Roleplay v0.1 HUD", annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord(' '):
                print("[EMERGENCY] User triggered EMERGENCY STOP!")
                driver.stop_all()
            elif key == ord('h'):
                print("[MANUAL] Triggering test HIT on CH0...")
                driver.hit(channel=0, power=50.0, decay_ms=400)

    except KeyboardInterrupt:
        print("
Stopping by user interrupt...")

    finally:
        print("Cleaning up resources...")
        driver.stop_all()
        driver.disconnect()
        cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete. Goodbye!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
