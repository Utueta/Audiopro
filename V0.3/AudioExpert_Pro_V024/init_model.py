import joblib
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def init():
    path = "models/audio_expert_rf.joblib"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Entrainement minimal
    X = np.array([[18000, 0.0], [12000, 0.1]])
    y = np.array([0, 1])
    clf = RandomForestClassifier().fit(X, y)
    joblib.dump(clf, path)

if __name__ == "__main__":
    init()
