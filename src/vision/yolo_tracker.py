"""
YOLO Pose Tracker for OpenHaptic-Roleplay
Performs real-time body keypoint tracking, sensitive zone defense detection, and struggle velocity analysis.
"""

import time
import math
import numpy as np
import cv2
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from ultralytics import YOLO


@dataclass
class PoseAnalysisResult:
    has_person: bool = False
    
    # Defense & Coverage States
    hands_covering_core: bool = False      # Hands covering groin/pelvic/magic conductor zone
    hands_covering_chest: bool = False     # Hands covering chest/heart
    is_defensive_stance: bool = False     # Arms crossed or tightly tucked
    
    # Body Dynamics
    struggle_index: float = 0.0           # 0.0 - 100.0 (Motion velocity & agitation)
    posture_label: str = "Neutral"        # "Standing", "Kneeling", "Defending", "Struggling"
    
    # Distances & Normalized Metrics
    wrist_to_core_dist: float = 1.0       # Normalized distance (0.0 to 1.0)
    leg_spread_ratio: float = 1.0         # Knees distance / Hip width
    
    # Keypoint Coordinates (x, y, conf)
    keypoints: Optional[np.ndarray] = None


class YOLOPoseTracker:
    def __init__(self, model_name: str = "yolov8n-pose.pt", conf_thresh: float = 0.45):
        self.conf_thresh = conf_thresh
        print(f"[YOLO] Loading YOLO Pose model ({model_name})...")
        self.model = YOLO(model_name)
        
        # Motion tracking state
        self._prev_keypoints: Optional[np.ndarray] = None
        self._prev_time: float = time.time()
        self._velocity_history: List[float] = []

    def process_frame(self, frame: np.ndarray) -> Tuple[PoseAnalysisResult, np.ndarray]:
        """
        Process a single BGR video frame.
        Returns: (PoseAnalysisResult, annotated_frame)
        """
        h, w = frame.shape[:2]
        now = time.time()
        dt = max(0.001, now - self._prev_time)
        self._prev_time = now

        # Run YOLO-Pose inference
        results = self.model(frame, conf=self.conf_thresh, verbose=False)
        annotated = frame.copy()
        
        result = PoseAnalysisResult()

        if not results or len(results[0].keypoints) == 0 or results[0].keypoints.data.shape[1] == 0:
            return result, annotated

        # Get first detected person's keypoints (17, 3) -> [x, y, conf]
        kpts = results[0].keypoints.data[0].cpu().numpy()
        result.has_person = True
        result.keypoints = kpts

        # Extract landmark keypoints
        # 5: L_shoulder, 6: R_shoulder, 9: L_wrist, 10: R_wrist, 11: L_hip, 12: R_hip, 13: L_knee, 14: R_knee
        l_sh, r_sh = kpts[5], kpts[6]
        l_wr, r_wr = kpts[9], kpts[10]
        l_hip, r_hip = kpts[11], kpts[12]
        l_knee, r_knee = kpts[13], kpts[14]

        # Calculate torso reference scale (distance between shoulders or hips)
        torso_size = 100.0
        if l_sh[2] > 0.3 and r_sh[2] > 0.3:
            torso_size = max(30.0, np.linalg.norm(l_sh[:2] - r_sh[:2]))
        elif l_hip[2] > 0.3 and r_hip[2] > 0.3:
            torso_size = max(30.0, np.linalg.norm(l_hip[:2] - r_hip[:2]))

        # Define Critical Body Zones:
        # 1. Chest Zone (Midpoint between shoulders)
        chest_pt = None
        if l_sh[2] > 0.3 and r_sh[2] > 0.3:
            chest_pt = (l_sh[:2] + r_sh[:2]) / 2.0

        # 2. Core / Pelvic Zone (Midpoint between hips, slightly lowered)
        core_pt = None
        if l_hip[2] > 0.3 and r_hip[2] > 0.3:
            core_pt = (l_hip[:2] + r_hip[:2]) / 2.0
            core_pt[1] += torso_size * 0.2  # Shift downward towards pelvic connector

        # Check Hand Coverage
        min_core_dist = 999.0
        min_chest_dist = 999.0

        for wrist in [l_wr, r_wr]:
            if wrist[2] > 0.35:
                if core_pt is not None:
                    d_core = np.linalg.norm(wrist[:2] - core_pt)
                    min_core_dist = min(min_core_dist, d_core)
                if chest_pt is not None:
                    d_chest = np.linalg.norm(wrist[:2] - chest_pt)
                    min_chest_dist = min(min_chest_dist, d_chest)

        # Thresholds relative to torso size
        core_thresh = torso_size * 0.75
        chest_thresh = torso_size * 0.65

        result.hands_covering_core = (min_core_dist < core_thresh)
        result.hands_covering_chest = (min_chest_dist < chest_thresh)
        result.is_defensive_stance = (result.hands_covering_core or result.hands_covering_chest)
        result.wrist_to_core_dist = min(1.0, min_core_dist / (torso_size * 2.0))

        # Calculate Struggle Velocity
        if self._prev_keypoints is not None:
            # Calculate mean displacement of valid visible joints
            valid_mask = (kpts[:, 2] > 0.4) & (self._prev_keypoints[:, 2] > 0.4)
            if np.sum(valid_mask) >= 4:
                disp = np.linalg.norm(kpts[valid_mask, :2] - self._prev_keypoints[valid_mask, :2], axis=1)
                speed_px_per_s = np.mean(disp) / dt
                
                # Normalize speed relative to torso size (torso/sec)
                speed_norm = (speed_px_per_s / torso_size) * 20.0
                self._velocity_history.append(speed_norm)
                if len(self._velocity_history) > 6:
                    self._velocity_history.pop(0)
                
                result.struggle_index = min(100.0, float(np.mean(self._velocity_history)))
        
        self._prev_keypoints = kpts.copy()

        # Determine Posture Label
        if result.struggle_index > 45.0:
            result.posture_label = "Struggling / Agitated"
        elif result.hands_covering_core:
            result.posture_label = "Defending Core Area"
        elif result.hands_covering_chest:
            result.posture_label = "Defending Chest"
        else:
            result.posture_label = "Neutral Stance"

        # Draw HUD overlays on frame
        self._draw_hud(annotated, result, chest_pt, core_pt, torso_size, kpts)

        return result, annotated

    def _draw_hud(self, img: np.ndarray, res: PoseAnalysisResult, chest_pt, core_pt, torso_size, kpts):
        h, w = img.shape[:2]

        # Draw Skeleton Bones
        SKELETON_EDGES = [
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16)
        ]
        for p1, p2 in SKELETON_EDGES:
            if kpts[p1, 2] > 0.35 and kpts[p2, 2] > 0.35:
                pt1 = (int(kpts[p1, 0]), int(kpts[p1, 1]))
                pt2 = (int(kpts[p2, 0]), int(kpts[p2, 1]))
                cv2.line(img, pt1, pt2, (0, 255, 200), 2, cv2.LINE_AA)

        # Draw Keypoint Circles
        for i in range(len(kpts)):
            if kpts[i, 2] > 0.35:
                pt = (int(kpts[i, 0]), int(kpts[i, 1]))
                cv2.circle(img, pt, 4, (0, 165, 255), -1)

        # Draw Sensitive Zones (Chest & Core)
        if chest_pt is not None:
            c_center = (int(chest_pt[0]), int(chest_pt[1]))
            color = (0, 0, 255) if res.hands_covering_chest else (255, 200, 0)
            cv2.circle(img, c_center, int(torso_size * 0.35), color, 2)
            cv2.putText(img, "CHEST", (c_center[0] - 25, c_center[1] - int(torso_size * 0.4)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        if core_pt is not None:
            c_center = (int(core_pt[0]), int(core_pt[1]))
            color = (0, 0, 255) if res.hands_covering_core else (0, 255, 100)
            cv2.circle(img, c_center, int(torso_size * 0.4), color, 2)
            cv2.putText(img, "CORE TARGET", (c_center[0] - 45, c_center[1] + int(torso_size * 0.55)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        # Draw Top HUD Dashboard Banner
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        # Status text
        status_color = (0, 0, 255) if res.is_defensive_stance else (0, 255, 0)
        cv2.putText(img, f"POSTURE: {res.posture_label}", (15, 30), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, status_color, 2)

        # Struggle index gauge
        gauge_w = 200
        gauge_val = int((res.struggle_index / 100.0) * gauge_w)
        cv2.putText(img, f"STRUGGLE: {res.struggle_index:.0f}%", (15, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.rectangle(img, (130, 48), (130 + gauge_w, 64), (80, 80, 80), 1)
        cv2.rectangle(img, (130, 48), (130 + gauge_val, 64), (0, 140, 255), -1)

        # Defense warning banner if triggered
        if res.hands_covering_core:
            cv2.putText(img, "[!] DEFENSE BREACH TRIGGERED", (w - 360, 45), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 0, 255), 2)
