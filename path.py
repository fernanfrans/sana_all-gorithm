import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/predict.py
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # root folder
model_path = os.path.join(PROJECT_ROOT, "rainnet_FINAL4.weights.h5")  # ✅ points to root

print(model_path)
