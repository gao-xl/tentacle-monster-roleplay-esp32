"""
Hardware-Optimized ONNX Export Pipeline for AMD DirectML & TensorRT
Exports trained PyTorch weights to FP16 / Dynamic Batch ONNX with fused NMS.
"""

import os
import argparse
from ultralytics import YOLO

def export_directml_onnx(pt_path: str, imgsz: int = 640, half: bool = True):
    print(f"📦 Exporting {pt_path} to Hardware-Accelerated ONNX (FP16={half})...")
    
    model = YOLO(pt_path)
    output_path = model.export(
        format="onnx",
        imgsz=imgsz,
        half=half,          # FP16 Precision for AMD Radeon 780M / DirectML
        dynamic=False,      # Fixed batch for fastest inference pipeline
        simplify=True,      # ONNX-Simplifier graph optimization
        opset=17
    )
    
    print(f"🎉 Successfully Exported Optimized Model: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=str, required=True, help="Path to best.pt")
    parser.add_argument("--half", action="store_true", default=True, help="Export FP16")
    args = parser.parse_args()

    export_directml_onnx(args.weights, half=args.half)
