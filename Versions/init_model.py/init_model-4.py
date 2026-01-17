import joblib, os, numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

def init():
    os.makedirs("models", exist_ok=True)
    # Centroid Hz, Clipping Ratio
    X = np.array([[18000, 0.0], [12000, 0.1], [20000, 0.0], [8000, 0.5]])
    y = np.array([0.05, 0.85, 0.02, 0.98])
    scaler = StandardScaler().fit(X)
    model = RandomForestRegressor(n_estimators=10).fit(scaler.transform(X), y)
    joblib.dump(model, "models/audio_expert_rf.joblib")
    joblib.dump(scaler, "models/scaler.pkl")
    print("✅ Artefacts ML initialisés.")

if __name__ == "__main__": init()

