import sqlite3
import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier
from send2trash import send2trash

class AudioModel:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()
        self.classifier = RandomForestClassifier(n_estimators=100)
        self.is_trained = False

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS audio_data (
                path TEXT PRIMARY KEY, hash TEXT, clipping REAL, snr REAL, 
                crackling REAL, roll_off REAL, score REAL, ml_score REAL,
                label TEXT, tag TEXT, timestamp REAL, tags_info TEXT)""")

    def save_analysis(self, data):
        with sqlite3.connect(self.db_path) as conn:
            query = """INSERT OR REPLACE INTO audio_data 
                       (path, hash, clipping, snr, crackling, roll_off, score, ml_score, tag, tags_info) 
                       VALUES (:path, :hash, :clipping, :snr, :crackling, :roll_off, :score, :ml_score, :tag, :tags_info)"""
            conn.execute(query, data)

    def train_ml(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("SELECT clipping, snr, crackling, roll_off, label FROM audio_data WHERE label IS NOT NULL", conn)
            if len(df) >= 5 and len(df['label'].unique()) > 1:
                X = df[['clipping', 'snr', 'crackling', 'roll_off']]
                y = df['label'].apply(lambda x: 1 if x == 'Défectueux' else 0)
                self.classifier.fit(X, y)
                self.is_trained = True
                return True
        return False

    def get_all_records(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("SELECT * FROM audio_data").fetchall()]
