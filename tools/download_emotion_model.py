"""
Tool to securely download the lightweight Emotion FER ONNX model.
Run this script once to enable local Micro-ONNX facial expression recognition.
"""
import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "emotion-ferplus-8.onnx")
# Using a widely trusted public ONNX Model Zoo link (FERPlus - 8 emotions)
URL = "https://github.com/onnx/models/raw/main/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"

def download_model():
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        
    if os.path.exists(MODEL_PATH):
        logging.info(f"Model already exists at {MODEL_PATH}")
        return

    logging.info(f"Downloading lightweight Emotion ONNX model to {MODEL_PATH}...")
    try:
        urllib.request.urlretrieve(URL, MODEL_PATH)
        logging.info("Download complete!")
    except Exception as e:
        logging.error(f"Failed to download model: {e}")
        logging.info("System will continue running in OpenCV-only heuristic mode (No FER).")

if __name__ == "__main__":
    download_model()
