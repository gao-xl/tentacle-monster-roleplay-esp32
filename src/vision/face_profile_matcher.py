"""
Privacy-Safe Local Face Recognition & User Profile Binding Engine (v0.1.0)
Extracts local facial embeddings using lightweight mathematical/ONNX cosine similarity,
automatically binding:
- Player Identity & Display Name
- Gender Tuning Settings (Male / Female / Delicate / Standard)
- Pre-Calibrated Endurance Limits (Tmax A/B)
- Play History, Defeat Count, and RPG Story Save Slots
"""

import os
import json
import time
import math
import logging
import numpy as np
import cv2
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger("FaceProfileMatcher")

PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "profiles")


@dataclass
class UserProfile:
    user_id: str
    display_name: str
    user_gender: str = "FEMALE"             # "FEMALE", "MALE", "NEUTRAL"
    sensitivity_level: str = "STANDARD"     # "DELICATE", "STANDARD", "HARDCORE"
    calibrated_tmax_a: float = 60.0         # Loop A Core limit
    calibrated_tmax_b: float = 75.0         # Loop B Leg limit
    face_embedding: Optional[List[float]] = None # Normalized face feature vector
    play_count: int = 0
    defeat_count: int = 0
    last_played: float = 0.0


class FaceProfileMatcher:
    def __init__(self):
        self.profiles: Dict[str, UserProfile] = {}
        self.active_profile: Optional[UserProfile] = None
        self._ensure_profiles_dir()
        self.load_all_profiles()

    def _ensure_profiles_dir(self):
        os.makedirs(PROFILES_DIR, exist_ok=True)

    def load_all_profiles(self):
        self.profiles.clear()
        for fname in os.listdir(PROFILES_DIR):
            if fname.endswith(".json"):
                fpath = os.path.join(PROFILES_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        prof = UserProfile(**data)
                        self.profiles[prof.user_id] = prof
                except Exception as e:
                    logger.error(f"[FaceMatcher] Failed to load {fpath}: {e}")

        logger.info(f"📂 [FaceMatcher] Loaded {len(self.profiles)} user profiles from disk.")

    def save_profile(self, profile: UserProfile) -> bool:
        fpath = os.path.join(PROFILES_DIR, f"{profile.user_id}.json")
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(asdict(profile), f, indent=2, ensure_ascii=False)
            self.profiles[profile.user_id] = profile
            logger.info(f"✅ [FaceMatcher] Saved profile '{profile.display_name}' ({profile.user_id})")
            return True
        except Exception as e:
            logger.error(f"[FaceMatcher] Save failed: {e}")
            return False

    def extract_face_embedding(self, frame: np.ndarray, kpts: np.ndarray) -> Optional[np.ndarray]:
        """Extracts a normalized 64-dim spatial-intensity facial descriptor purely locally."""
        h, w = frame.shape[:2]
        # Use head keypoints (0: Nose, 1: LEye, 2: REye, 3: LEar, 4: REar)
        head_pts = [i for i in range(5) if kpts[i, 2] > 0.4]
        if len(head_pts) < 3:
            return None

        xs = [kpts[i, 0] for i in head_pts]
        ys = [kpts[i, 1] for i in head_pts]
        x_c, y_c = int(np.mean(xs)), int(np.mean(ys))
        face_w = int((max(xs) - min(xs)) * 2.2)
        if face_w < 30: face_w = 64

        fx1, fx2 = max(0, x_c - face_w), min(w, x_c + face_w)
        fy1, fy2 = max(0, y_c - face_w), min(h, y_c + face_w)

        if fx2 <= fx1 or fy2 <= fy1:
            return None

        face_roi = frame[fy1:fy2, fx1:fx2]
        face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        face_resized = cv2.resize(face_gray, (32, 32), interpolation=cv2.INTER_AREA)

        # Compute 64-dim Spatial Block Intensity Vector (Local LBP-like histogram)
        blocks = []
        for r in range(4):
            for c in range(4):
                block = face_resized[r*8:(r+1)*8, c*8:(c+1)*8]
                blocks.append(np.mean(block))
                blocks.append(np.std(block))
                blocks.append(np.median(block))
                blocks.append(float(np.sum(block > 128)))

        emb = np.array(blocks, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb /= norm
        return emb

    def identify_or_create(self, frame: np.ndarray, kpts: np.ndarray) -> Tuple[Optional[UserProfile], float]:
        """Matches face against database. Returns (Matched Profile, Cosine Similarity)."""
        emb = self.extract_face_embedding(frame, kpts)
        if emb is None:
            return self.active_profile, 0.0

        best_match: Optional[UserProfile] = None
        best_sim = 0.0

        for prof in self.profiles.values():
            if prof.face_embedding is not None:
                db_emb = np.array(prof.face_embedding, dtype=np.float32)
                sim = float(np.dot(emb, db_emb)) # Cosine similarity
                if sim > best_sim:
                    best_sim = sim
                    best_match = prof

        # Threshold: 0.82 similarity = verified same person
        if best_match and best_sim >= 0.82:
            self.active_profile = best_match
            best_match.last_played = time.time()
            return best_match, best_sim
        else:
            return None, best_sim

    def register_new_profile(
        self,
        display_name: str,
        gender: str,
        frame: np.ndarray,
        kpts: np.ndarray,
        tmax_a: float = 60.0,
        tmax_b: float = 75.0
    ) -> Optional[UserProfile]:
        """Enrolls a new face into local profile library."""
        emb = self.extract_face_embedding(frame, kpts)
        if emb is None:
            return None

        uid = f"user_{int(time.time()*1000)}"
        new_prof = UserProfile(
            user_id=uid,
            display_name=display_name,
            user_gender=gender,
            calibrated_tmax_a=tmax_a,
            calibrated_tmax_b=tmax_b,
            face_embedding=emb.tolist(),
            play_count=1,
            last_played=time.time()
        )
        self.save_profile(new_prof)
        self.active_profile = new_prof
        return new_prof


global_face_matcher = FaceProfileMatcher()
