import os
import json
import sqlite3
import hashlib
import time
import requests
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from mutagen import File as MutagenFile
import pygame

# ===================== CONFIGURATION =====================
DB_FILE = "audio_history.db"
LLM_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "llama2" # ou mistral, llama3, etc.
EXTENSIONS = (".wav", ".mp3", ".flac", ".wma", ".aac", ".ogg", ".m4a")

# ===================== BASE DE DONNÉES =====================
class AudioDB:
    def __init__(self, db_path=DB_FILE):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                hash_128 TEXT,
                clipping_ratio REAL,
                snr REAL,
                crackling_rate REAL,
                spectral_flatness REAL,
                quality_score REAL,
                ml_suspicion_score REAL,
                label TEXT, -- 'Bon', 'Défectueux'
                tags TEXT,  -- 'ban', 'duplicate'
                error_timestamp REAL,
                file_size INTEGER,
                duration REAL,
                is_duplicate INTEGER DEFAULT 0,
                last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def get_training_data(self):
        cursor = self.conn.execute("""
            SELECT clipping_ratio, snr, crackling_rate, quality_score, label 
            FROM audio_files WHERE label IS NOT NULL AND label != ''
        """)
        rows = cursor.fetchall()
        if not rows: return None, None
        X = np.array([r[:-1] for r in rows])
        y = np.array([1 if r[-1] == 'Défectueux' else 0 for r in rows])
        return X, y

    def upsert_file(self, data: dict):
        keys = list(data.keys())
        values = list(data.values())
        sql = f"INSERT OR REPLACE INTO audio_files ({', '.join(keys)}) VALUES ({', '.join(['?']*len(keys))})"
        self.conn.execute(sql, values)
        self.conn.commit()

# ===================== ANALYSEUR DE SIGNAL =====================
class AudioAnalyzer:
    @staticmethod
    def get_hash(path: str) -> str:
        """Génère un hash Blake2b 128-bit."""
        h = hashlib.blake2b(digest_size=16)
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def analyze(path: str) -> Dict:
        size = os.path.getsize(path)
        if size == 0:
            return {"error": "empty", "quality_score": 0}

        try:
            y, sr = librosa.load(path, sr=None, duration=60)
            duration = librosa.get_duration(y=y, sr=sr)
            if duration == 0: return {"error": "empty", "quality_score": 0}

            # 1. Clipping (Distorsion)
            
            clipping_ratio = np.sum(np.abs(y) >= 0.95) / len(y)
            
            # 2. SNR
            rms = librosa.feature.rms(y=y)
            snr = 20 * np.log10(np.mean(rms) / (np.std(rms) + 1e-6))
            
            # 3. Craquements
            diff = np.abs(np.diff(y))
            crackling_rate = np.sum(diff > 0.4) / len(diff)

            # 4. Spectral Flatness
            flatness = np.mean(librosa.feature.spectral_flatness(y=y))

            # 5. Global Score (Heuristique)
            q_score = 100 * (1.0 - (clipping_ratio * 3 + crackling_rate * 5 + (1 / max(snr, 1))))
            q_score = max(0, min(100, q_score))

            # Premier timestamp suspect
            bad_idx = np.where((np.abs(y) >= 0.95) | (np.insert(diff, 0, 0) > 0.4))[0]
            error_ts = bad_idx[0] / sr if len(bad_idx) > 0 else 0

            return {
                "clipping_ratio": float(clipping_ratio),
                "snr": float(snr),
                "crackling_rate": float(crackling_rate),
                "spectral_flatness": float(flatness),
                "quality_score": float(q_score),
                "error_timestamp": float(error_ts),
                "duration": float(duration),
                "file_size": size
            }
        except Exception as e:
            return {"error": str(e), "quality_score": 0}

# ===================== ML PIPELINE =====================
class MLPipeline:
    def __init__(self, db: AudioDB):
        self.db = db
        self.clf = RandomForestClassifier(n_estimators=100)
        self.is_trained = False
        self._train()

    def _train(self):
        
        X, y = self.db.get_training_data()
        if X is not None and len(np.unique(y)) > 1:
            self.clf.fit(X, y)
            self.is_trained = True

    def get_score(self, m: Dict) -> float:
        if not self.is_trained:
            # Cold Start Formula
            # $$suspicion\_score = w1 \cdot Clipping + w2 \cdot (15 - SNR) + w3 \cdot Crackling + w4 \cdot (60 - Quality)$$
            score = (0.4 * m['clipping_ratio'] * 10) + \
                    (0.2 * max(0, 15 - m['snr']) / 15) + \
                    (0.3 * m['crackling_rate'] * 15) + \
                    (0.1 * max(0, 60 - m['quality_score']) / 60)
            return min(1.0, float(score))
        
        feat = np.array([[m['clipping_ratio'], m['snr'], m['crackling_rate'], m['quality_score']]])
        return float(self.clf.predict_proba(feat)[0][1])

# ===================== MAIN ENGINE =====================
def main():
    db = AudioDB()
    ml = MLPipeline(db)
    analyzer = AudioAnalyzer()
    
    # 1. Paramétrage
    folder = input("Dossier à analyser [./audio_samples] : ") or "./audio_samples"
    print("\n1: 100 premiers | 2: Custom | 3: TOUS | 4: TOUS sauf tag 'ban'")
    opt = input("Option : ")
    
    # Scan récursif
    files = []
    for root, _, filenames in os.walk(folder):
        for f in filenames:
            if f.lower().endswith(EXTENSIONS):
                files.append(os.path.join(root, f))

    # Filtrage Option 4
    if opt == "4":
        cursor = db.conn.execute("SELECT file_path FROM audio_files WHERE tags LIKE '%ban%'")
        banned = {r[0] for r in cursor.fetchall()}
        files = [f for f in files if f not in banned]

    # Limite
    if opt == "1": files = files[:100]
    elif opt == "2": 
        n = int(input("Nombre de fichiers : "))
        files = files[:n]

    # 2. Analyse Parallèle & Doublons
    print(f"🔎 Analyse de {len(files)} fichiers...")
    results = []
    hash_map = {} # Pour stat doublons
    
    def process(p):
        h = analyzer.get_hash(p)
        m = analyzer.analyze(p)
        
        entry = {"file_path": p, "hash_128": h}
        
        # Gestion vide / erreur
        if "error" in m:
            entry.update({"label": "Défectueux", "tags": "ban", "ml_suspicion_score": 1.0, "quality_score": 0})
            db.upsert_file(entry)
            return None

        # Détection doublon
        cursor = db.conn.execute("SELECT id FROM audio_files WHERE hash_128=? AND file_path!=?", (h, p))
        is_dup = 1 if cursor.fetchone() else 0
        
        score = ml.get_score(m)
        entry.update({**m, "ml_suspicion_score": score, "is_duplicate": is_dup})
        if is_dup: entry["tags"] = "duplicate"
        
        db.upsert_file(entry)
        return {"file_id": p, **m, "ml_score": score}

    with ThreadPoolExecutor() as exe:
        raw_res = list(exe.map(process, files))
        results = [r for r in raw_res if r is not None]

    # 3. LLM Ranking
    print("🤖 Envoi au LLM pour arbitrage...")
    prompt = f"Analyse ces données audio et renvoie UNIQUEMENT le format file_id:score pour les plus suspects.\nDonnées: {json.dumps(results[:20])}"
    try:
        resp = requests.post(LLM_URL, json={"model": LLM_MODEL, "prompt": prompt, "stream": False}, timeout=30)
        llm_out = resp.json().get('response', "")
        print(f"Réponse LLM : {llm_out}")
    except:
        print("⚠️ LLM non joignable, utilisation du score ML pur.")

    # 4. Révision Interactive
    pygame.mixer.init()
    # Tri par suspicion descendante
    results.sort(key=lambda x: x['ml_score'], reverse=True)
    
    print("\n--- RÉVISION INTERACTIVE ---")
    for r in results:
        path = r['file_id']
        print(f"\nFichier : {os.path.basename(path)} (Score: {r['ml_score']:.2f})")
        
        while True:
            cmd = input("[E]couter [D]éfectueux [B]on [S]auter [Q]uitter : ").upper()
            if cmd == 'E':
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(start=r['error_timestamp'])
            elif cmd == 'D':
                db.conn.execute("UPDATE audio_files SET label='Défectueux', tags='ban' WHERE file_path=?", (path,))
                db.conn.commit()
                break
            elif cmd == 'B':
                db.conn.execute("UPDATE audio_files SET label='Bon' WHERE file_path=?", (path,))
                db.conn.commit()
                break
            elif cmd == 'S': break
            elif cmd == 'Q': return

    # Stats finales
    dups = db.conn.execute("SELECT COUNT(*) FROM audio_files WHERE is_duplicate=1").fetchone()[0]
    print(f"\n✅ Terminé. Doublons détectés : {dups}")

if __name__ == "__main__":
    main()
