"""
Local Privacy-Safe Vision Context Extractor (v2.0)
Extracts environmental & physiological cues purely locally without cloud APIs.
1. OpenCV Math Cues: Environment Brightness, Clothes Color, Motion Blur (Agitation).
2. Micro-ONNX Cues: Facial Expression Recognition (FER) - if model exists.
"""

import os
import cv2
import numpy as np
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("LocalVisionContext")

class LocalVisionContextExtractor:
    def __init__(self, model_path: str = "models/emotion.onnx"):
        self.emotion_labels = ['Neutral', 'Happy', 'Surprise', 'Sad', 'Anger/Pain', 'Disgust', 'Fear/ClosedEyes', 'Contempt']
        self.ort_session = None
        
        # Try loading the lightweight FER ONNX model if available
        if os.path.exists(model_path):
            try:
                import onnxruntime as ort
                self.ort_session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
                logger.info(f"[VisionContext] Emotion ONNX model loaded successfully from {model_path}.")
            except Exception as e:
                logger.warning(f"[VisionContext] Failed to load Emotion ONNX: {e}")
        else:
            logger.info("[VisionContext] Emotion ONNX not found. Running in OpenCV-only heuristic mode.")

    def analyze_context(self, frame: np.ndarray, kpts: np.ndarray) -> Dict[str, Any]:
        """
        frame: BGR numpy array
        kpts: YOLO pose keypoints (N, 3) where [:, 0] is X, [:, 1] is Y, [:, 2] is confidence
        """
        h, w = frame.shape[:2]
        context = {
            "brightness": "NORMAL",
            "clothes_color": "UNKNOWN",
            "face_emotion": "UNSEEN",
            "is_shaking": False
        }

        # 1. Overall Environment Brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_luma = np.mean(gray)
        if avg_luma < 60:
            context["brightness"] = "昏暗 (DARK)"
        elif avg_luma > 180:
            context["brightness"] = "明亮 (BRIGHT)"
        else:
            context["brightness"] = "正常 (NORMAL)"

        # 2. Clothing Color Extraction (Torso Bounding Box)
        # Use shoulders (5,6) and hips (11,12)
        valid_torso = all(kpts[i, 2] > 0.4 for i in [5, 6, 11, 12])
        if valid_torso:
            xs = [kpts[i, 0] for i in [5, 6, 11, 12]]
            ys = [kpts[i, 1] for i in [5, 6, 11, 12]]
            x_min, x_max = max(0, int(min(xs))), min(w, int(max(xs)))
            y_min, y_max = max(0, int(min(ys))), min(h, int(max(ys)))
            
            if x_max > x_min and y_max > y_min:
                torso_roi = frame[y_min:y_max, x_min:x_max]
                hsv_torso = cv2.cvtColor(torso_roi, cv2.COLOR_BGR2HSV)
                mean_hsv = np.mean(hsv_torso, axis=(0, 1))
                H, S, V = mean_hsv
                
                # Simple Color Heuristic Map
                if V < 60:
                    context["clothes_color"] = "深色/黑色 (DARK)"
                elif S < 40 and V > 180:
                    context["clothes_color"] = "浅色/白色 (LIGHT/WHITE)"
                elif H < 15 or H > 165:
                    context["clothes_color"] = "红色/暖色 (RED/WARM)"
                elif 90 < H < 130:
                    context["clothes_color"] = "蓝色/冷色 (BLUE/COLD)"
                else:
                    context["clothes_color"] = "混合色 (MIXED)"

        # 3. Face Extraction: Emotion & Motion Blur (Sweat/Shaking)
        # Use head keypoints (0: Nose, 1: LEye, 2: REye, 3: LEar, 4: REar)
        head_pts = [i for i in range(5) if kpts[i, 2] > 0.4]
        if len(head_pts) >= 3:
            xs = [kpts[i, 0] for i in head_pts]
            ys = [kpts[i, 1] for i in head_pts]
            x_c, y_c = int(np.mean(xs)), int(np.mean(ys))
            
            # Estimate face size based on eye/ear distance
            face_w = int((max(xs) - min(xs)) * 2.0)
            if face_w < 20: face_w = 60
            
            fx1, fx2 = max(0, x_c - face_w), min(w, x_c + face_w)
            fy1, fy2 = max(0, y_c - face_w), min(h, y_c + face_w)
            
            if fx2 > fx1 and fy2 > fy1:
                face_roi = frame[fy1:fy2, fx1:fx2]
                face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                
                # A. Motion Blur / Shaking Detection (Laplacian Variance)
                lap_var = cv2.Laplacian(face_gray, cv2.CV_64F).var()
                if lap_var < 50.0:  # Highly blurred = moving fast or sweating/out of focus
                    context["is_shaking"] = True
                
                # B. Emotion ONNX Inference
                if self.ort_session is not None:
                    try:
                        # FERPlus typically expects 64x64 grayscale
                        resized = cv2.resize(face_gray, (64, 64))
                        input_data = np.expand_dims(np.expand_dims(resized, 0), 0).astype(np.float32)
                        input_name = self.ort_session.get_inputs()[0].name
                        outputs = self.ort_session.run(None, {input_name: input_data})
                        
                        scores = outputs[0][0]
                        max_idx = np.argmax(scores)
                        emotion = self.emotion_labels[max_idx]
                        
                        # Map generic FER labels to Roleplay Context
                        if emotion in ['Anger/Pain', 'Sad', 'Fear/ClosedEyes']:
                            context["face_emotion"] = "痛苦/紧闭双眼 (PAIN/CLOSED)"
                        elif emotion == 'Happy':
                            context["face_emotion"] = "挑逗/微笑 (SMIRK)"
                        else:
                            context["face_emotion"] = "面无表情/忍耐 (NEUTRAL/ENDURING)"
                    except Exception:
                        pass

        return context
