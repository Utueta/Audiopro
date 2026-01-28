import sqlite3
import pandas as pd
import queue
import threading
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
import numpy as np

class AudioModel:
    def __init__(self, db_path):
        self.db_path = db_path
        self.write_queue = queue.Queue()
        self.model_path = "trained_model.pkl"
        self._init_db()
        
        # Initialisation ML
        self.ml_model = RandomForestRegressor(n_estimators=100)
        self.load_model()
        
        # Thread de base de données (Asynchrone)
        self.db_thread = threading.Thread(target=self._worker, daemon=True)
        self.db_thread.start()

    def _init_db(self):
        """Initialise la table avec TOUTES les colonnes (Originales + Nouvelles)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS audio_data (
                path TEXT PRIMARY KEY, 
                hash TEXT, 
                score REAL, 
                label TEXT, 
                artist TEXT, 
                title TEXT, 
                bitrate INTEGER, 
                comment TEXT, 
                is_duplicate INTEGER, 
                original_path TEXT,
                defect_timestamps TEXT,
                snr REAL,
                clipping REAL,
                is_fake_hq REAL,
                phase_corr REAL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.ml_model = joblib.load(self.model_path)
            except: pass

    def predict_suspicion(self, features_list):
        """Prend [score, snr, clipping, is_fake_hq, phase_corr]"""
        try:
            features = np.array([features_list])
            return float(self.ml_model.predict(features)[0])
        except:
            return features_list[0] # Fallback sur le score initial

    def retrain(self):
        """Réentraînement sur les 5 critères de la V4.1"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql("""
                    SELECT score, snr, clipping, is_fake_hq, phase_corr, label 
                    FROM audio_data WHERE label IN ('Bon', 'Ban')
                """, conn)
            
            if len(df) >= 10:
                X = df[['score', 'snr', 'clipping', 'is_fake_hq', 'phase_corr']].fillna(0)
                y = df['label'].apply(lambda x: 1 if x == 'Ban' else 0)
                
                self.ml_model.fit(X, y)
                joblib.dump(self.ml_model, self.model_path)
                return True
            return False
        except Exception as e:
            print(f"Erreur réentraînement : {e}")
            return False

    def mark_file(self, path, label, comment=""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE audio_data SET label = ?, comment = ? WHERE path = ?", 
                        (label, comment, path))
        self.retrain()

    def get_dynamic_thresholds(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql("SELECT score FROM audio_data WHERE label IS NOT NULL", conn)
            if not df.empty:
                return {'p50': float(df['score'].quantile(0.5)), 'p90': float(df['score'].quantile(0.9))}
        except: pass
        return {'p50': 0.5, 'p90': 0.8}

    def _worker(self):
        """Le Worker qui empêche l'application de ramer pendant l'écriture DB"""
        while True:
            item = self.write_queue.get()
            if item is None: break
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""INSERT OR REPLACE INTO audio_data 
                    (path, hash, score, artist, title, bitrate, defect_timestamps, 
                     snr, clipping, is_fake_hq, phase_corr) 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (item['path'], item['hash'], item['score'], 
                     item['meta']['artist'], item['meta']['title'], item['meta']['bitrate'], 
                     str(item.get('defect_timestamps', [])),
                     item.get('snr', 0), item.get('clipping', 0),
                     item.get('is_fake_hq', 0), item.get('phase_corr', 1.0))
                )
            self.write_queue.task_done()

    def add_to_queue(self, data):
        self.write_queue.put(data)
