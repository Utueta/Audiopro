import joblib, os, numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

def init():
    os.makedirs("models", exist_ok=True)
    X = np.array([[18000, 0.0], [12000, 0.15], [20000, 0.0], [8000, 0.45]])
    y = np.array([0.05, 0.88, 0.01, 0.96]) 
    scaler = StandardScaler().fit(X)
    model = RandomForestRegressor(n_estimators=10).fit(scaler.transform(X), y)
    joblib.dump(model, "models/audio_expert_rf.joblib")
    joblib.dump(scaler, "models/scaler.pkl")
    print("✅ Pipeline ML Obsidian Initialisé.")

if __name__ == "__main__": init()
