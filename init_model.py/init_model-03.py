
import joblib, os, numpy as np

from sklearn.ensemble import RandomForestClassifier


def init():

    path = "models/audio_expert_rf.joblib"

    os.makedirs(os.path.dirname(path), exist_ok=True)

    X = np.array([[18000, 0.0], [12000, 0.1], [20000, 0.0], [9000, 0.5]])

    y = np.array([0, 1, 0, 1])

    clf = RandomForestClassifier(n_estimators=10).fit(X, y)

    joblib.dump(clf, path)

    print(f"✅ Modèle amorcé : {path}")


if __name__ == "__main__": init()

