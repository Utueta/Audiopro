import os
import json
import sqlite3
import hashlib
import time
import requests
import numpy as np
import librosa
import pygame
from concurrent.futures import ThreadPoolExecutor
from sklearn.ensemble import RandomForestClassifier

# ===================== CONFIGURATION =====================
DB_NAME = "audio_history.db"
LLM_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "llama2"
AUDIO_EXT = ('.wav', '.mp3', '.flac', '.wma', '.aac', '.ogg', '.m4a')

# ===================== BASE DE DONNÉES =====================
class AudioHistoryDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                hash_128 TEXT,
                clipping REAL, snr REAL, crackling REAL, spectral_flatness REAL,
                quality_score REAL, ml_score REAL,
                label TEXT, tag TEXT, comment TEXT,
                error_ts REAL, file_size INTEGER, duration REAL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def save(self, data: dict):
        cols = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        self.conn.execute(f"INSERT OR REPLACE INTO history ({cols}) VALUES ({placeholders})", list(data.values()))
        self.conn.commit()

# ===================== MOTEUR ML (APPRENTISSAGE INCRÉMENTAL) =====================
class QualityEngine:
    def __init__(self, db: AudioHistoryDB):
        self.db = db
        self.model = RandomForestClassifier(n_estimators=100)
        self.is_trained = False
        self.refresh()

    def refresh(self):
        """Ré-entraînement sur l'historique complet à chaque appel"""
        cursor = self.db.conn.execute("SELECT clipping, snr, crackling, quality_score, label FROM history WHERE label IS NOT NULL")
        rows = cursor.fetchall()
        if rows:
            X = [[r['clipping'], r['snr'], r['crackling'], r['quality_score']] for r in rows if r['clipping'] is not None]
            y = [1 if r['label'] == 'Défectueux' else 0 for r in rows if r['clipping'] is not None]
            if len(set(y)) > 1:
                self.model.fit(X, y)
                self.is_trained = True
                print("🔄 Modèle ML mis à jour avec les nouvelles données.")

    def get_score(self, m: dict) -> float:
        if not self.is_trained:
            # Formule Cold Start
            score = (0.35 * m['clipping'] * 10) + (0.20 * max(0, 15 - m['snr']) / 15) + \
                    (0.30 * m['crackling'] * 15) + (0.15 * max(0, 60 - m['quality_score']) / 60)
            return min(1.0, float(score))
        return float(self.model.predict_proba([[m['clipping'], m['snr'], m['crackling'], m['quality_score']]])[0][1])

# ===================== ANALYSEUR UNIFIÉ =====================
class UniversalAnalyzer:
    @staticmethod
    def analyze(path: str) -> dict:
        size = os.path.getsize(path)
        if size == 0: return {"error": "BAN: Fichier 0kb", "reason": "Taille nulle"}

        try:
            # Test de décodage
            y, sr = librosa.load(path, sr=None, duration=45)
            dur = librosa.get_duration(y=y, sr=sr)
            if dur <= 0: return {"error": "BAN: Durée nulle", "reason": "Durée 0.0s"}

            # Métriques
            clipping = np.sum(np.abs(y) >= 0.98) / len(y)
            rms = librosa.feature.rms(y=y)
            snr = 20 * np.log10(np.mean(rms) / (np.std(rms) + 1e-6))
            diff = np.abs(np.diff(y))
            crackling = np.sum(diff > 0.5) / len(diff)
            flatness = np.mean(librosa.feature.spectral_flatness(y=y))
            q_score = max(0, min(100, 100 * (1.0 - (clipping * 2.5 + crackling * 4 + (1 / max(snr, 1))))))
            
            bad_idx = np.where((np.abs(y) >= 0.98) | (np.insert(diff, 0, 0) > 0.5))[0]
            
            return {
                "clipping": float(clipping), "snr": float(snr), "crackling": float(crackling),
                "spectral_flatness": float(flatness), "quality_score": float(q_score),
                "error_ts": float(bad_idx[0]/sr if len(bad_idx) > 0 else 0),
                "duration": float(dur), "file_size": size
            }
        except Exception:
            return {"error": "BAN: Décodage impossible", "reason": "Fichier corrompu"}

# ===================== LOGIQUE PRINCIPALE =====================
def main():
    db = AudioHistoryDB()
    engine = QualityEngine(db)
    pygame.mixer.init()
    
    print("\n--- AUDIO ANALYZER V2.2 ---")
    folder = input("Dossier à analyser [./audio_samples] : ") or "./audio_samples"
    print("\n[1] 100 premiers | [2] Custom | [3] TOUS | [4] TOUS (sauf bannis)")
    choice = input("Option : ")

    all_files = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if f.lower().endswith(AUDIO_EXT)]
    if choice == "4":
        banned = {r['file_path'] for r in db.conn.execute("SELECT file_path FROM history WHERE tag='ban'").fetchall()}
        all_files = [f for f in all_files if f not in banned]

    # ... (Limitation selon option 1 ou 2)
    
    print(f"🚀 Traitement de {len(all_files)} fichiers...")
    results = []
    stats_ban = {"Taille nulle": 0, "Durée 0.0s": 0, "Fichier corrompu": 0}

    def process(path):
        h = hashlib.blake2b(open(path, "rb").read(8192), digest_size=16).hexdigest()
        res = UniversalAnalyzer.analyze(path)
        
        entry = {"file_path": path, "hash_128": h}
        if "error" in res:
            entry.update({"label": "Défectueux", "tag": "ban", "ml_score": 1.0, "comment": res["error"]})
            db.save(entry)
            stats_ban[res["reason"]] += 1
            return None

        dup = db.conn.execute("SELECT id FROM history WHERE hash_128=? AND file_path!=?", (h, path)).fetchone()
        m_score = engine.get_score(res)
        entry.update({**res, "ml_score": m_score, "tag": "duplicate" if dup else None})
        db.save(entry)
        return {"file_id": path, **res, "ml_score": m_score}

    with ThreadPoolExecutor() as exe:
        results = [r for r in list(exe.map(process, all_files)) if r]

    # Révision interactive
    results.sort(key=lambda x: x['ml_score'], reverse=True)
    for r in results:
        print(f"\n📁 {os.path.basename(r['file_id'])} (Score Suspicion: {r['ml_score']:.2f})")
        while True:
            cmd = input("[E]couter [D]éfectueux [B]on [S]auter [Q]uitter : ").upper()
            if cmd == 'E':
                pygame.mixer.music.load(r['file_id'])
                pygame.mixer.music.play(start=r['error_ts'])
            elif cmd in ['D', 'B']:
                label, tag = ("Défectueux", "ban") if cmd == 'D' else ("Bon", None)
                db.conn.execute("UPDATE history SET label=?, tag=? WHERE file_path=?", (label, tag, r['file_id']))
                db.conn.commit()
                engine.refresh() # APPRENTISSAGE INCRÉMENTAL
                break
            elif cmd == 'S': break
            elif cmd == 'Q': break
        if cmd == 'Q': break

    # EXPORTATION DES STATISTIQUES
    print("\n" + "="*30)
    print("📊 RAPPORT FINAL D'ANALYSE")
    print("="*30)
    print(f"Fichiers analysés avec succès : {len(results)}")
    print(f"Fichiers bannis (automatique) : {sum(stats_ban.values())}")
    for k, v in stats_ban.items():
        if v > 0: print(f"  - {k} : {v}")
    
    dups = db.conn.execute("SELECT COUNT(*) as c FROM history WHERE tag='duplicate'").fetchone()['c']
    print(f"Doublons détectés en base : {dups}")
    
    with open("dernière_analyse_stats.json", "w") as f:
        json.dump({"date": time.ctime(), "stats_ban": stats_ban, "valid_files": len(results), "duplicates": dups}, f, indent=4)
    print("\n✅ Statistiques exportées dans 'dernière_analyse_stats.json'")

if __name__ == "__main__":
    main()
