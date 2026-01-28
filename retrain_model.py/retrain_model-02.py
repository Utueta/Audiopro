"""
Audiopro v0.3.1
Handles model fitting, Z-Score scaling, and artifact serialization for the Sentinel Brain.
"""
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from pathlib import Path

def train_sentinel():
    weights_dir = Path("core/brain/weights")
    weights_dir.mkdir(parents=True, exist_ok=True)

    # Technical training data
    X = np.array([[30, 0], [25, 1], [15, 10], [5, 50], [2, 100]])
    y = np.array([0, 0, 0, 1, 1]) # 0=Clean, 1=Corrupt

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_scaled, y)

    joblib.dump(model, weights_dir / "random_forest.pkl")
    joblib.dump(scaler, weights_dir / "scaler_v0.3.pkl")

if __name__ == "__main__":
    train_sentinel()
