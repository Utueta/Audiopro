import os
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

def create_training_set():
    """
    Generates a synthetic ground-truth dataset for the Obsidian Brain.
    Features: [Spectral Centroid (Hz), Clipping Ratio (%), SNR (dB), Phase Corr]
    """
    # X: [Hz, Clip, SNR, Phase]
    X = np.array([
        [19000, 0.0, 35.0, 0.95],  # High-Fidelity Studio
        [17500, 0.01, 28.0, 0.85], # Clean FLAC
        [12000, 0.15, 15.0, 0.40], # Upscaled YouTube Rip (Fake HQ)
        [8000, 0.45, 10.0, 0.10],  # Transcoded Garbage
        [15000, 0.05, 20.0, 0.70], # Borderline / Grey Zone
    ])
    
    # y: Probability of being "FAKE/BAD" (0.0 = Perfect, 1.0 = Ban)
    y = np.array([0.02, 0.08, 0.85, 0.98, 0.45])
    
    return X, y

def bootstrap_brain():
    """
    Initializes the Audiopro ML artifacts (Model + Scaler).
    Ensures the 'Deep Obsidian' view has deterministic data to consume.
    """
    print("--- Audiopro Random Forest Brain v0.2.5 Bootloader ---")
    
    # 1. Setup Environment
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "audio_expert_rf.joblib")
    scaler_path = os.path.join(model_dir, "scaler.pkl")

    # 2. Data Preparation
    X, y = create_training_set()
    
    # 3. Fit Scaler (Critical for Z-Score Normalization)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 4. Train Regressor (Optimized for 0.0-1.0 Score range)
    model = RandomForestRegressor(
        n_estimators=50,
        max_depth=5,
        random_state=42
    )
    model.fit(X_scaled, y)
    
    # 5. Export Artifacts
    try:
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        print(f"✅ SUCCESS: Model saved to {model_path}")
        print(f"✅ SUCCESS: Scaler saved to {scaler_path}")
        
        # Validation Test
        test_val = np.array([[10000, 0.2, 12.0, 0.3]])
        test_scaled = scaler.transform(test_val)
        prediction = model.predict(test_scaled)[0]
        print(f"--- Calibration Check: {prediction:.4f} (Expected ~0.8-0.9) ---")
        
    except Exception as e:
        print(f"❌ BOOTSTRAP FAILED: {str(e)}")

if __name__ == "__main__":
    bootstrap_brain()
