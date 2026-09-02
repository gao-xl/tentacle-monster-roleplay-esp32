"""
Export script for YOLO11-Pose optimized for AMD Radeon iGPU (780M/680M)
Generates FP16 ONNX with fixed spatial dimensions for DirectML / OpenVINO / TensorRT.
"""

import os
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Export YOLO11-Pose for AMD Hardware Acceleration")
    parser.add_argument("--model", default="yolo11n-pose.pt", help="Ultralytics model name or path")
    parser.add_argument("--imgsz", type=int, default=320, help="Image size (320 is optimal for iGPU 100+ FPS)")
    parser.add_argument("--output-dir", default="models", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"[*] Loading model: {args.model}...")
    model = YOLO(args.model)

    print(f"[*] Exporting to ONNX (imgsz={args.imgsz}, half=True for AMD iGPU)...")
    exported_path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        half=True,           # FP16 acceleration for Radeon 780M
        simplify=True,       # ONNX graph optimization
        opset=17,
        dynamic=False        # Static shape ensures optimal memory allocation
    )

    dest = os.path.join(args.output_dir, "yolo11n-pose.onnx")
    if os.path.exists(dest):
        os.remove(dest)
    os.rename(exported_path, dest)
    print(f"[OK] Successfully exported: {dest}")

if __name__ == "__main__":
    main()
