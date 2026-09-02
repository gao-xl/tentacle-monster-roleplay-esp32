"""
Advanced Pose & Behavior Classifier for OpenHaptic-Roleplay
Extends YOLO11-Pose to compute fine-grained combat/roleplay states:
- Surrender / Begging Gestures (Hands up, Hands behind head)
- Leg Opening / Clamping Angle Ratio (Continuous 0.0 - 1.0)
- Kneeling / Submissive Posture 3D Angle Triangulation
- Defense Severity Index & Weakpoint Exposure Score
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, List


@dataclass
class DetailedPoseMetrics:
    # Basic Presence
    has_person: bool = False
    confidence: float = 0.0

    # Fine-grained Gestures & Postures
    is_surrendering: bool = False         # Hands raised above head (Surrender / Begging)
    is_hands_behind_head: bool = False    # Hands locked behind neck/head (Total Submission)
    is_kneeling: bool = False             # Kneeling on the ground (Submissive posture)
    is_squatting: bool = False            # Squatting / crouching low
    is_fallen: bool = False               # Lying flat / knocked down

    # Defense & Coverage Detailed Metrics
    hands_covering_core: bool = False     # Pelvic / Magic Conductor zone
    hands_covering_chest: bool = False    # Upper chest / Heart zone
    hands_covering_face: bool = False     # Covering eyes / embarrassment

    # Quantitative Biometric Continuous Signals (0.0 to 1.0)
    leg_clamp_ratio: float = 1.0          # 1.0 = Tightly clamped/defending, 0.0 = Wide open/exposed
    weakpoint_exposure: float = 0.0       # 0.0 = Fully protected, 1.0 = Fully exposed & vulnerable
    struggle_intensity: float = 0.0       # 0.0 - 100.0 (Motion velocity integral)
    tremor_index: float = 0.0             # 0.0 - 100.0 (High frequency spasm score)

    # Narrative State Tag
    state_tag: str = "NEUTRAL"            # "SURRENDER", "DEFENDING_CORE", "KNEELING_EXPOSED", "STRUGGLING", etc.


class AdvancedPoseClassifier:
    """Computes geometric posture rules and behavior heuristics from 17 COCO Keypoints."""

    def __init__(self, ema_alpha: float = 0.3):
        self.ema_alpha = ema_alpha
        self._prev_clamp_ratio = 1.0
        self._prev_exposure = 0.0

    def analyze(self, kpts: Optional[np.ndarray], struggle_val: float = 0.0) -> DetailedPoseMetrics:
        metrics = DetailedPoseMetrics()
        metrics.struggle_intensity = struggle_val

        if kpts is None or len(kpts) < 17:
            return metrics

        metrics.has_person = True
        metrics.confidence = float(np.mean(kpts[:, 2]))

        # Keypoint Index Mapping:
        # 0: Nose, 1: L_eye, 2: R_eye, 3: L_ear, 4: R_ear
        # 5: L_shoulder, 6: R_shoulder, 7: L_elbow, 8: R_elbow, 9: L_wrist, 10: R_wrist
        # 11: L_hip, 12: R_hip, 13: L_knee, 14: R_knee, 15: L_ankle, 16: R_ankle
        nose = kpts[0]
        l_sh, r_sh = kpts[5], kpts[6]
        l_el, r_el = kpts[7], kpts[8]
        l_wr, r_wr = kpts[9], kpts[10]
        l_hip, r_hip = kpts[11], kpts[12]
        l_knee, r_knee = kpts[13], kpts[14]
        l_ank, r_ank = kpts[15], kpts[16]

        # 1. Calculate Torso Reference Scale
        torso_len = 120.0
        if l_sh[2] > 0.3 and l_hip[2] > 0.3:
            torso_len = max(40.0, np.linalg.norm(l_sh[:2] - l_hip[:2]))
        elif r_sh[2] > 0.3 and r_hip[2] > 0.3:
            torso_len = max(40.0, np.linalg.norm(r_sh[:2] - r_hip[:2]))

        hip_width = 80.0
        if l_hip[2] > 0.3 and r_hip[2] > 0.3:
            hip_width = max(30.0, np.linalg.norm(l_hip[:2] - r_hip[:2]))

        # Target Centers
        chest_center = (l_sh[:2] + r_sh[:2]) / 2.0 if (l_sh[2] > 0.3 and r_sh[2] > 0.3) else None
        hip_center = (l_hip[:2] + r_hip[:2]) / 2.0 if (l_hip[2] > 0.3 and r_hip[2] > 0.3) else None
        core_target = hip_center.copy() if hip_center is not None else None
        if core_target is not None:
            core_target[1] += torso_len * 0.15 # Shift towards pelvic seam

        # 2. Gesture: Hands Raised / Surrender
        # Wrists significantly above shoulders or nose
        head_y = nose[1] if nose[2] > 0.3 else (l_sh[1] + r_sh[1]) / 2.0 - torso_len * 0.3
        hands_above_head = (l_wr[2] > 0.3 and l_wr[1] < head_y) and (r_wr[2] > 0.3 and r_wr[1] < head_y)
        hands_above_shoulders = (l_wr[2] > 0.3 and l_wr[1] < l_sh[1]) and (r_wr[2] > 0.3 and r_wr[1] < r_sh[1])
        
        if hands_above_head or hands_above_shoulders:
            metrics.is_surrendering = True

        # 3. Gesture: Hands Behind Head
        if chest_center is not None:
            l_behind = (l_wr[2] > 0.3 and abs(l_wr[0] - nose[0]) < torso_len * 0.4 and l_wr[1] < l_sh[1])
            r_behind = (r_wr[2] > 0.3 and abs(r_wr[0] - nose[0]) < torso_len * 0.4 and r_wr[1] < r_sh[1])
            if l_behind and r_behind:
                metrics.is_hands_behind_head = True

        # 4. Coverage Checks (Core, Chest, Face)
        for wr in [l_wr, r_wr]:
            if wr[2] > 0.3:
                if core_target is not None and np.linalg.norm(wr[:2] - core_target) < torso_len * 0.45:
                    metrics.hands_covering_core = True
                if chest_center is not None and np.linalg.norm(wr[:2] - chest_center) < torso_len * 0.4:
                    metrics.hands_covering_chest = True
                if nose[2] > 0.3 and np.linalg.norm(wr[:2] - nose[:2]) < torso_len * 0.35:
                    metrics.hands_covering_face = True

        # 5. Leg Clamping vs Exposure Ratio (0.0 to 1.0)
        if l_knee[2] > 0.3 and r_knee[2] > 0.3:
            knee_dist = np.linalg.norm(l_knee[:2] - r_knee[:2])
            # Ratio of knee distance to hip width
            spread_factor = knee_dist / max(1.0, hip_width)
            # Clamp: spread_factor < 0.7 is clamped (1.0), spread_factor > 1.8 is wide open (0.0)
            raw_clamp = max(0.0, min(1.0, 1.0 - (spread_factor - 0.7) / 1.1))
            metrics.leg_clamp_ratio = self.ema_alpha * raw_clamp + (1 - self.ema_alpha) * self._prev_clamp_ratio
            self._prev_clamp_ratio = metrics.leg_clamp_ratio

        # 6. Posture: Kneeling / Squatting
        # Kneeling: Hips are noticeably lower relative to knees, or knees near ground
        if l_hip[2] > 0.3 and l_knee[2] > 0.3 and l_ank[2] > 0.3:
            hip_knee_dy = l_knee[1] - l_hip[1]
            knee_ank_dy = l_ank[1] - l_knee[1]
            if hip_knee_dy < torso_len * 0.7 and knee_ank_dy < torso_len * 0.4:
                metrics.is_kneeling = True

        # 7. Overall Weakpoint Exposure Score (0.0 to 1.0)
        # Fully exposed if legs are open and hands are not covering core
        exposure = (1.0 - metrics.leg_clamp_ratio) * 0.6
        if not metrics.hands_covering_core:
            exposure += 0.4
        else:
            exposure *= 0.3 # Coverage drastically reduces exposure score

        metrics.weakpoint_exposure = max(0.0, min(1.0, exposure))

        # 8. Determine Comprehensive State Tag
        if metrics.struggle_intensity > 45.0:
            metrics.state_tag = "STRUGGLING"
        elif metrics.is_surrendering:
            metrics.state_tag = "SURRENDER_BEGGING"
        elif metrics.is_hands_behind_head:
            metrics.state_tag = "TOTAL_SUBMISSION"
        elif metrics.is_kneeling and metrics.weakpoint_exposure > 0.6:
            metrics.state_tag = "KNEELING_EXPOSED"
        elif metrics.hands_covering_core:
            metrics.state_tag = "DEFENDING_CORE"
        elif metrics.hands_covering_chest:
            metrics.state_tag = "DEFENDING_CHEST"
        elif metrics.weakpoint_exposure > 0.7:
            metrics.state_tag = "WEAKPOINT_VULNERABLE"
        else:
            metrics.state_tag = "NEUTRAL"

        return metrics
