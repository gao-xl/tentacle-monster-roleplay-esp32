"""
YOLO-Pose 26 Keypoint Tracker (Halpe-26 Topology) for OpenHaptic-Roleplay
Supports 26 dense human keypoints:
- 0-16: Standard COCO Body Keypoints
- 17: Head Top
- 18: Neck (Cervical / Throat Center)
- 19: Hip Center / Pelvis Root (Direct Core Weakpoint Anchor)
- 20-22: Left Foot (BigToe, SmallToe, Heel)
- 23-25: Right Foot (BigToe, SmallToe, Heel)

Computes high-precision Pelvic Core Defense, Foot Plantarflexion (Toe Curl/Spasm),
and Spine Angle Subjugation.
"""

import math
import time
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from ..core.onnx_infer import ONNXInfer, get_providers_hw_accel


@dataclass
class Pose26AnalysisResult:
    has_person: bool = False
    confidence: float = 0.0

    # 1. 26-Point Exclusive Anchors
    core_weakpoint_pt: Optional[Tuple[float, float]] = None   # Point 19: Pelvis Root
    neck_pt: Optional[Tuple[float, float]] = None              # Point 18: Neck Center
    spine_vector: Optional[Tuple[float, float]] = None         # Neck -> Pelvis Root Vector

    # 2. High-Precision Defense & Covering
    hands_covering_core: bool = False     # High-precision distance to Point 19
    hands_covering_chest: bool = False    # Distance to Point 18/Mid-shoulder
    hands_covering_neck: bool = False     # Hands choking / guarding neck
    wrist_to_core_dist_norm: float = 1.0  # 0.0 (direct contact) to 1.0 (far away)

    # 3. Foot Physiology & Tremor Metrics (Points 20-25)
    toe_curl_index: float = 0.0           # 0.0 - 100.0 (Toes curling / Foot spasm under stimulation)
    feet_tiptoeing: bool = False          # True if heels are raised (tiptoe / trembling legs)
    foot_tremor_score: float = 0.0        # High-frequency foot agitation

    # 4. Whole Body Stance & Subjugation
    leg_spread_ratio: float = 1.0         # Knees spread / Hip width
    is_kneeling: bool = False             # Submissive kneeling on floor
    is_surrendering: bool = False         # Hands up
    is_spine_collapsed: bool = False      # Spine vector tilted > 60 deg

    # 5. Summary Scores
    struggle_score: float = 0.0           # 0.0 - 100.0
    vulnerability_score: float = 0.0      # 0.0 (guarded) - 1.0 (fully exposed)
    posture_tag: str = "NEUTRAL"
    keypoints: Optional[np.ndarray] = None


# 26-Point Halpe Skeleton Edges for Rendering
SKELETON_26_EDGES = [
    # Head & Spine
    (17, 0), (0, 18), (18, 19),
    # Upper Body
    (18, 5), (18, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    # Lower Body & Pelvis Anchor
    (19, 11), (19, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    # Left Foot Triangle
    (15, 20), (15, 22), (20, 21), (21, 22),
    # Right Foot Triangle
    (16, 23), (16, 25), (23, 24), (24, 25)
]


class YOLOPose26Tracker:
    def __init__(
        self,
        model_path: str = "models/yolo11n-pose26.onnx",
        imgsz: int = 640,
        conf_thresh: float = 0.35,
        iou_thresh: float = 0.45
    ):
        self.imgsz = imgsz
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        
        # Load unified inference engine with AMD DirectML / OpenVINO / TensorRT
        providers = get_providers_hw_accel()
        self.infer = ONNXInfer(model_path, providers=providers, use_io_binding=True, fp16_input=True)
        self.input_name = self.infer.input_names[0]

        self._prev_kpts: Optional[np.ndarray] = None
        self._prev_time = time.time()
        self._vel_history: List[float] = []

    def _preprocess(self, frame: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        h, w = frame.shape[:2]
        scale = min(self.imgsz / h, self.imgsz / w)
        nh, nw = int(h * scale), int(w * scale)
        img = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        top = (self.imgsz - nh) // 2
        bottom = self.imgsz - nh - top
        left = (self.imgsz - nw) // 2
        right = self.imgsz - nw - left
        img_padded = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

        img_norm = (img_padded.astype(np.float16) / 255.0).transpose((2, 0, 1))
        return np.expand_dims(img_norm, 0), scale, (left, top)

    def process_frame(self, frame: np.ndarray) -> Tuple[Pose26AnalysisResult, np.ndarray]:
        h, w = frame.shape[:2]
        now = time.time()
        dt = max(0.001, now - self._prev_time)
        self._prev_time = now

        input_tensor, scale, pads = self._preprocess(frame)
        outputs = self.infer({self.input_name: input_tensor})

        # Process 26-Point Predictions
        # Output shape typically: (1, 83, NumAnchors) where 83 = 4(box) + 1(conf) + 26*3(kpts)
        preds = outputs[0][0].T
        obj_conf = preds[:, 4]
        mask = obj_conf > self.conf_thresh

        result = Pose26AnalysisResult()
        annotated = frame.copy()

        if not np.any(mask):
            return result, annotated

        preds = preds[mask]
        obj_conf = obj_conf[mask]

        # NMS
        boxes = preds[:, :4].copy()
        boxes[:, 0] = (boxes[:, 0] - boxes[:, 2] / 2 - pads[0]) / scale
        boxes[:, 1] = (boxes[:, 1] - boxes[:, 3] / 2 - pads[1]) / scale
        boxes[:, 2] /= scale
        boxes[:, 3] /= scale

        indices = cv2.dnn.NMSBoxes(boxes.tolist(), obj_conf.tolist(), self.conf_thresh, self.iou_thresh)
        if len(indices) == 0:
            return result, annotated

        best_idx = indices[0] if isinstance(indices, (list, tuple)) else indices[0]
        kpts_raw = preds[best_idx][5:].reshape(-1, 3) # (26, 3)

        # Scale keypoints back to original frame
        kpts = np.zeros((len(kpts_raw), 3), dtype=np.float32)
        kpts[:, 0] = (kpts_raw[:, 0] - pads[0]) / scale
        kpts[:, 1] = (kpts_raw[:, 1] - pads[1]) / scale
        kpts[:, 2] = kpts_raw[:, 2]

        result.has_person = True
        result.confidence = float(obj_conf[best_idx])
        result.keypoints = kpts

        # 1. Extract 26 Specialized Anchors
        # 18: Neck, 19: Hip Center (Core Conductor Anchor)
        if len(kpts) >= 26:
            if kpts[19, 2] > 0.3:
                result.core_weakpoint_pt = (float(kpts[19, 0]), float(kpts[19, 1]))
            if kpts[18, 2] > 0.3:
                result.neck_pt = (float(kpts[18, 0]), float(kpts[18, 1]))

            # Spine Vector (Neck -> Pelvis)
            if result.neck_pt and result.core_weakpoint_pt:
                dx = result.core_weakpoint_pt[0] - result.neck_pt[0]
                dy = result.core_weakpoint_pt[1] - result.neck_pt[1]
                spine_len = math.sqrt(dx*dx + dy*dy)
                result.spine_vector = (dx, dy)
                # Angle relative to vertical
                spine_angle = math.degrees(math.atan2(abs(dx), max(1.0, dy)))
                if spine_angle > 55.0:
                    result.is_spine_collapsed = True

            # 2. Foot Plantarflexion & Toe Curler Index (Points 20-25)
            # L: 20(BigToe), 22(Heel); R: 23(BigToe), 25(Heel)
            toe_angles = []
            for toe_idx, heel_idx in [(20, 22), (23, 25)]:
                if kpts[toe_idx, 2] > 0.3 and kpts[heel_idx, 2] > 0.3:
                    f_dx = kpts[toe_idx, 0] - kpts[heel_idx, 0]
                    f_dy = kpts[toe_idx, 1] - kpts[heel_idx, 1]
                    # Vertical drop of toes relative to heel
                    if f_dy > 15: # Toes pointed down / foot arched
                        toe_angles.append(min(100.0, f_dy * 2.5))
            if toe_angles:
                result.toe_curl_index = float(np.mean(toe_angles))

        # 3. High-Precision Pelvic Defense Check against Point 19
        l_wr, r_wr = kpts[9], kpts[10]
        torso_scale = 120.0
        if result.neck_pt and result.core_weakpoint_pt:
            torso_scale = max(40.0, np.linalg.norm(np.array(result.neck_pt) - np.array(result.core_weakpoint_pt)))

        if result.core_weakpoint_pt is not None:
            c_pt = np.array(result.core_weakpoint_pt)
            min_dist = 999.0
            for wr in [l_wr, r_wr]:
                if wr[2] > 0.3:
                    d = np.linalg.norm(wr[:2] - c_pt)
                    min_dist = min(min_dist, d)
            
            result.wrist_to_core_dist_norm = min(1.0, min_dist / (torso_scale * 1.5))
            result.hands_covering_core = (min_dist < torso_scale * 0.45)

        # 4. Struggle & Velocity
        if self._prev_kpts is not None and len(self._prev_kpts) == len(kpts):
            valid = (kpts[:, 2] > 0.35) & (self._prev_kpts[:, 2] > 0.35)
            if np.sum(valid) >= 6:
                disp = np.linalg.norm(kpts[valid, :2] - self._prev_kpts[valid, :2], axis=1)
                speed = (np.mean(disp) / dt) / torso_scale * 20.0
                self._vel_history.append(speed)
                if len(self._vel_history) > 6: self._vel_history.pop(0)
                result.struggle_score = min(100.0, float(np.mean(self._vel_history)))

        self._prev_kpts = kpts.copy()

        # 5. Render HUD with 26-Point Topology
        self._render_hud_26(annotated, result, kpts)

        return result, annotated

    def _render_hud_26(self, img: np.ndarray, res: Pose26AnalysisResult, kpts: np.ndarray):
        h, w = img.shape[:2]

        # Draw 26-Point Dense Skeleton
        for p1, p2 in SKELETON_26_EDGES:
            if p1 < len(kpts) and p2 < len(kpts):
                if kpts[p1, 2] > 0.35 and kpts[p2, 2] > 0.35:
                    pt1 = tuple(map(int, kpts[p1, :2]))
                    pt2 = tuple(map(int, kpts[p2, :2]))
                    # Spine & Pelvis in Neon Magenta, Limbs in Cyan
                    edge_color = (255, 0, 200) if (p1 in [18, 19] or p2 in [18, 19]) else (0, 240, 255)
                    cv2.line(img, pt1, pt2, edge_color, 2, cv2.LINE_AA)

        # Draw Exclusive Target Markers
        # Point 19: Pelvis Core Target
        if res.core_weakpoint_pt:
            cx, cy = map(int, res.core_weakpoint_pt)
            ring_color = (0, 0, 255) if res.hands_covering_core else (0, 255, 100)
            cv2.circle(img, (cx, cy), 18, ring_color, 2)
            cv2.drawMarker(img, (cx, cy), ring_color, cv2.MARKER_TILTED_CROSS, 14, 2)
            cv2.putText(img, "POINT 19 // CORE", (cx - 55, cy + 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, ring_color, 1)

        # Top HUD Bar
        cv2.rectangle(img, (0, 0), (w, 50), (10, 15, 25), -1)
        cv2.line(img, (0, 50), (w, 50), (0, 240, 255), 1)
        
        status_txt = f"HALPE-26 POSE // CORE DEFENSE: {'LOCKED [!]' if res.hands_covering_core else 'EXPOSED'}"
        txt_color = (0, 0, 255) if res.hands_covering_core else (0, 255, 0)
        cv2.putText(img, status_txt, (15, 32), cv2.FONT_HERSHEY_DUPLEX, 0.65, txt_color, 1)

        if res.toe_curl_index > 25:
            cv2.putText(img, f"FOOT SPASM: {res.toe_curl_index:.0f}%", (w - 220, 32), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 100, 255), 1)
