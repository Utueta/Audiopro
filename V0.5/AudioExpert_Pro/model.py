import os, sqlite3, joblib, numpy as np
from PySide6.QtCore import QMutex, QMutexLocker

class FraudModel:
    def __init__(self, config):
        self.cfg = config['ml_engine']
        self.db_path = config['paths']['db_path']
        self.model_path = config['paths']['model_path']
        self.scaler_path = config['paths']['scaler_path']
        self.lock = QMutex()
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS scans (hash TEXT PRIMARY KEY, score REAL, user_val INTEGER)")

    def predict(self, m):
        try:
            model = joblib.load(self.model_path)
            scaler = joblib.load(self.scaler_path)
            X = np.array([[m['centroid'], m['clipping']]])
            return float(model.predict(scaler.transform(X))[0])
        except:
            # Fallback hybride physique
            w = self.cfg['initial_weights']
            score = (0.8 if m['centroid'] < 16500 else 0.1) * w['spectral_cut']
            score += m['clipping'] * w['clipping']
            return min(score, 1.0)

    def save_analysis(self, m, s):
        with QMutexLocker(self.lock):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO scans (hash, score) VALUES (?,?)", (m['hash'], s))

    def update_feedback(self, h, v):
        with QMutexLocker(self.lock):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE scans SET user_val = ? WHERE hash = ?", (1 if v else 0, h))

