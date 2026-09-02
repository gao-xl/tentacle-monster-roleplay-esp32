"""
YOLO-Pose 26 with Dynamic T-Pose Calibration (v3.0)
Eliminates hardcoded thresholds by calibrating to the user's specific skeletal proportions:
- Torso Height (Neck to Pelvis)
- Leg Length (Hip to Ankle)
- Shoulder Width
Dynamic thresholds are generated based on these baseline pixel measurements.
"""

import math
import time
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
from ..core.onnx_infer import ONNXInfer, get_providers_hw_accel
from .local_context import LocalVisionContextExtractor
from .one_euro_filter import Skeleton26OneEuroFilter


@dataclass
class PlayerCalibrationData:
    is_calibrated: bool = False
    shoulder_width: float = 100.0
    torso_height: float = 120.0
    leg_length: float = 150.0
    
    # Dynamically generated thresholds
    thresh_toe_curl: float = 15.0
    thresh_hands_core_dist: float = 50.0


@dataclass
class Pose26AnalysisResult:
    has_person: bool = False
    confidence: float = 0.0

    core_weakpoint_pt: Optional[Tuple[float, float]] = None
    neck_pt: Optional[Tuple[float, float]] = None
    
    hands_covering_core: bool = False
    hands_extended_to_camera: bool = False
    
    toe_curl_index: float = 0.0
    is_spine_collapsed: bool = False
    is_surrendering: bool = False
    
    struggle_score: float = 0.0
    keypoints: Optional[np.ndarray] = None
    
    # Local Vision Context
    env_brightness: str = "NORMAL"
    clothes_color: str = "UNKNOWN"
    face_emotion: str = "UNSEEN"
    is_face_shaking: bool = False


SKELETON_26_EDGES = [
    (17, 0), (0, 18), (18, 19),
    (18, 5), (18, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (19, 11), (19, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (15, 20), (15, 22), (20, 21), (21, 22),
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
        
        providers = get_providers_hw_accel()
        self.infer = ONNXInfer(model_path, providers=providers, use_io_binding=True, fp16_input=True)
        self.input_name = self.infer.input_names[0]

        self._prev_kpts: Optional[np.ndarray] = None
        self._prev_time = time.time()
        self._vel_history: List[float] = []
        
        self.local_context_ext = LocalVisionContextExtractor(model_path="models/emotion-ferplus-8.onnx")
        self.one_euro_filter = Skeleton26OneEuroFilter(num_kpts=26, mincutoff=1.0, beta=0.04)
        
        # v3.0 Calibration System
        self.calibration = PlayerCalibrationData()
        self._calib_frames = []

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

        preds = outputs[0][0].T
        obj_conf = preds[:, 4]
        mask = obj_conf > self.conf_thresh

        result = Pose26AnalysisResult()
        annotated = frame.copy()

        if not np.any(mask):
            return result, annotated

        preds = preds[mask]
        obj_conf = obj_conf[mask]

        boxes = preds[:, :4].copy()
        boxes[:, 0] = (boxes[:, 0] - boxes[:, 2] / 2 - pads[0]) / scale
        boxes[:, 1] = (boxes[:, 1] - boxes[:, 3] / 2 - pads[1]) / scale
        boxes[:, 2] /= scale
        boxes[:, 3] /= scale

        indices = cv2.dnn.NMSBoxes(boxes.tolist(), obj_conf.tolist(), self.conf_thresh, self.iou_thresh)
        if len(indices) == 0:
            return result, annotated

        best_idx = indices[0] if isinstance(indices, (list, tuple)) else indices[0]
        kpts_raw = preds[best_idx][5:].reshape(-1, 3)

        kpts = np.zeros((len(kpts_raw), 3), dtype=np.float32)
        kpts[:, 0] = (kpts_raw[:, 0] - pads[0]) / scale
        kpts[:, 1] = (kpts_raw[:, 1] - pads[1]) / scale
        kpts[:, 2] = kpts_raw[:, 2]

        # Apply Temporal One-Euro Filter to eliminate jitter & occlusion jumps
        kpts = self.one_euro_filter.filter_keypoints(kpts, timestamp=now)

        result.has_person = True
        result.confidence = float(obj_conf[best_idx])
        result.keypoints = kpts

        # ==========================================
        # 1. DYNAMIC CALIBRATION PHASE
        # ==========================================
        if not self.calibration.is_calibrated:
            if self._run_calibration(kpts):
                self.calibration.is_calibrated = True
                print(f"[CALIBRATION COMPLETE] Torso: {self.calibration.torso_height:.1f}px, Leg: {self.calibration.leg_length:.1f}px")
            
            # Draw Calibration HUD
            cv2.putText(annotated, f"CALIBRATING SKELETON... {len(self._calib_frames)}/30", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
            return result, annotated

        # ==========================================
        # 2. CALIBRATED PHYSIOLOGICAL ANALYSIS
        # ==========================================
        if kpts[19, 2] > 0.3: result.core_weakpoint_pt = (float(kpts[19, 0]), float(kpts[19, 1]))
        if kpts[18, 2] > 0.3: result.neck_pt = (float(kpts[18, 0]), float(kpts[18, 1]))

        # Dynamic Spine Collapse
        if result.neck_pt and result.core_weakpoint_pt:
            dx = result.core_weakpoint_pt[0] - result.neck_pt[0]
            dy = result.core_weakpoint_pt[1] - result.neck_pt[1]
            spine_angle = math.degrees(math.atan2(abs(dx), max(1.0, dy)))
            if spine_angle > 55.0:
                result.is_spine_collapsed = True

        # Dynamic Toe Curl Spasm (Threshold based on 10% of Leg Length)
        toe_angles = []
        for toe_idx, heel_idx in [(20, 22), (23, 25)]:
            if kpts[toe_idx, 2] > 0.3 and kpts[heel_idx, 2] > 0.3:
                f_dy = kpts[toe_idx, 1] - kpts[heel_idx, 1]
                # Normalize against calibrated threshold instead of hardcoded '15'
                if f_dy > self.calibration.thresh_toe_curl:
                    toe_angles.append(min(100.0, (f_dy / self.calibration.thresh_toe_curl) * 20.0))
        if toe_angles:
            result.toe_curl_index = float(np.mean(toe_angles))

        # Dynamic Core Defense & Hands Reach
        l_sh, r_sh = kpts[5], kpts[6]
        l_el, r_el = kpts[7], kpts[8]
        l_wr, r_wr = kpts[9], kpts[10]

        for el, wr, sh in [(l_el, l_wr, l_sh), (r_el, r_wr, r_sh)]:
            if el[2] > 0.3 and wr[2] > 0.3 and sh[2] > 0.3:
                upper_arm_len = np.linalg.norm(el[:2] - sh[:2])
                forearm_len = np.linalg.norm(wr[:2] - el[:2])
                if forearm_len < upper_arm_len * 0.35:
                    result.hands_extended_to_camera = True

        if result.core_weakpoint_pt is not None:
            c_pt = np.array(result.core_weakpoint_pt)
            min_dist = 999.0
            for wr in [l_wr, r_wr]:
                if wr[2] > 0.3:
                    min_dist = min(min_dist, np.linalg.norm(wr[:2] - c_pt))
            
            # Check against normalized torso core distance (approx 40% of torso height)
            if min_dist < self.calibration.thresh_hands_core_dist and not result.hands_extended_to_camera:
                result.hands_covering_core = True

        # Motion Velocity
        if self._prev_kpts is not None and len(self._prev_kpts) == len(kpts):
            valid = (kpts[:, 2] > 0.35) & (self._prev_kpts[:, 2] > 0.35)
            if np.sum(valid) >= 6:
                disp = np.linalg.norm(kpts[valid, :2] - self._prev_kpts[valid, :2], axis=1)
                speed = (np.mean(disp) / dt) / self.calibration.torso_height * 30.0
                self._vel_history.append(speed)
                if len(self._vel_history) > 6: self._vel_history.pop(0)
                result.struggle_score = min(100.0, float(np.mean(self._vel_history)))

        # Local Vision Context
        ctx = self.local_context_ext.analyze_context(frame, kpts)
        result.env_brightness = ctx["brightness"]
        result.clothes_color = ctx["clothes_color"]
        result.face_emotion = ctx["face_emotion"]
        result.is_face_shaking = ctx["is_shaking"]

        self._prev_kpts = kpts.copy()
        self._render_hud_26(annotated, result, kpts)

        return result, annotated

    def _run_calibration(self, kpts: np.ndarray) -> bool:
        """Collects 30 frames to calculate baseline skeletal proportions."""
        required = [5, 6, 18, 19, 11, 13, 15] # shoulders, neck, core, left leg chain
        if not all(kpts[i, 2] > 0.4 for i in required):
            return False
            
        self._calib_frames.append(kpts)
        if len(self._calib_frames) < 30:
            return False
            
        # Compute medians to ignore outliers
        s_ws, t_hs, l_ls = [], [], []
        for f in self._calib_frames:
            s_ws.append(np.linalg.norm(f[5, :2] - f[6, :2]))
            t_hs.append(np.linalg.norm(f[18, :2] - f[19, :2]))
            l_ls.append(np.linalg.norm(f[11, :2] - f[13, :2]) + np.linalg.norm(f[13, :2] - f[15, :2]))
            
        self.calibration.shoulder_width = float(np.median(s_ws))
        self.calibration.torso_height = float(np.median(t_hs))
        self.calibration.leg_length = float(np.median(l_ls))
        
        # Set dynamic physiological thresholds
        self.calibration.thresh_toe_curl = self.calibration.leg_length * 0.08
        self.calibration.thresh_hands_core_dist = self.calibration.torso_height * 0.45
        
        return True

    def _render_hud_26(self, img: np.ndarray, res: Pose26AnalysisResult, kpts: np.ndarray):
        for p1, p2 in SKELETON_26_EDGES:
            if p1 < len(kpts) and p2 < len(kpts):
                if kpts[p1, 2] > 0.35 and kpts[p2, 2] > 0.35:
                    pt1 = tuple(map(int, kpts[p1, :2]))
                    pt2 = tuple(map(int, kpts[p2, :2]))
                    cv2.line(img, pt1, pt2, (0, 240, 255), 2, cv2.LINE_AA)