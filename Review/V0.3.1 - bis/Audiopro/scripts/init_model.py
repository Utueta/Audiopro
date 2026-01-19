"""
Audiopro Model Initializer v0.3.1
- Generates baseline Random Forest weights (.pkl).
- v0.3.1 Fix: Calibrates for 3-feature vector [SNR, Clipping, Suspicion].
"""

import joblib
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

def generate_v03_artifacts():
    weights_dir = Path("core/brain/weights")
    weights_dir.mkdir(parents=True, exist_ok=True)

    # v0.3.1 Protocol: [SNR, Clipping Count, Suspicion Score]
    # Clean: High SNR (40+), 0 Clipping, Low Suspicion (<0.2)
    clean = np.random.normal(loc=[45, 0, 0.1], scale=[5, 0, 0.05], size=(200, 3))
    
    # Corrupt: Low SNR (<15), High Clipping (100+), High Suspicion (>0.8)
    corrupt = np.random.normal(loc=[10, 200, 0.85], scale=[5, 50, 0.1], size=(200, 3))
    
    X = np.vstack((clean, corrupt))
    y = np.hstack((np.ones(200), np.zeros(200))) # 1=Clean, 0=Corrupt

    # 1. Fit & Export Scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, weights_dir / "scaler_v0.3.pkl")

    # 2. Train & Export Model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    joblib.dump(model, weights_dir / "random_forest.pkl")
    
    print(f"v0.3.1 Artifacts generated in {weights_dir}")

if __name__ == "__main__":
    generate_v03_artifacts()
