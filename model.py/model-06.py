import os
import sqlite3
import joblib
from PySide6.QtCore import QMutex, QMutexLocker

class FraudModel:
    def __init__(self, config):
        self.cfg = config['ml_engine']
        self.db_path = config['paths']['db_path']
        self.lock = QMutex() # Axe C : Thread-Safety
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS scans 
                (hash TEXT PRIMARY KEY, filename TEXT, score REAL, user_val INTEGER)""")

    def predict(self, metrics):
        w = self.cfg['initial_weights']
        score = (0.85 if metrics['is_fake_hq'] else 0.1) * w['spectral_cut']
        score += metrics['clipping'] * w['clipping']
        return min(float(score), 1.0)

    def save_analysis(self, metrics, score):
        with QMutexLocker(self.lock):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT OR REPLACE INTO scans (hash, filename, score) VALUES (?, ?, ?)",
                             (metrics['hash'], metrics['filename'], score))

    def update_feedback(self, f_hash, val):
        with QMutexLocker(self.lock):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE scans SET user_val = ? WHERE hash = ?", (1 if val else 0, f_hash))
