"""
Audiopro Model Initializer v0.2.5
- Generates baseline Random Forest weights
- Calibrates the Z-Score Scaler for feature normalization
- Populates core/brain/weights/ for the first system boot
"""

import os
import joblib
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

def generate_baseline_weights():
    # 1. Ensure Directory Structure
    weights_dir = Path("core/brain/weights")
    weights_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Initializing ML Brain weights in: {weights_dir}")

    # 2. Generate Synthetic Industrial Training Data
    # Features: [SNR (dB), Clipping Count, Suspicion Score]
    # Labels: 1 (CLEAN), 0 (CORRUPT)
    
    # Class 1: High SNR, No Clipping, Low Suspicion (Clean)
    clean_data = np.random.normal(loc=[35, 0, 0.1], scale=[5, 0, 0.05], size=(100, 3))
    
    # Class 0: Low SNR, High Clipping, High Suspicion (Corrupt)
    corrupt_data = np.random.normal(loc=[10, 50, 0.8], scale=[5, 20, 0.1], size=(100, 3))
    
    X = np.vstack((clean_data, corrupt_data))
    y = np.hstack((np.ones(100), np.zeros(100)))

    # 3. Initialize and Fit Scaler
    # Essential for ensuring SNR (0-100) doesn't overwhelm Suspicion (0-1)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. Train Baseline Random Forest
    # Using 50 estimators for a balance of speed and accuracy
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_scaled, y)

    # 5. Persist Artifacts
    model_path = weights_dir / "random_forest_v01.pkl"
    scaler_path = weights_dir / "scaler_v01.pkl"
    
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"[+] Model saved: {model_path}")
    print(f"[+] Scaler saved: {scaler_path}")
    print("[!] ML Brain Primed. You can now launch app.py.")

if __name__ == "__main__":
    generate_baseline_weights()
