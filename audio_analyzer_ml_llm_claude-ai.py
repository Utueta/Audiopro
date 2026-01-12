"""
Analyseur Audio Avancé avec ML + LLM + Base de Données
Architecture hybride : Random Forest ML + LLM local + SQLite
Fichier: audio_analyzer_ml_llm.py

=== DÉPENDANCES COMPLÈTES POUR LINUX ===

# Paquets système (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3-pip python3-dev portaudio19-dev libsndfile1 ffmpeg \
    libportaudio2 libasound2-dev python3-pyaudio sqlite3

# Paquets Python
pip install librosa soundfile numpy scipy requests pygame mutagen \
    scikit-learn pandas joblib sqlalchemy

# LLM local (Ollama)
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
ollama pull llama2

=== AUTRES DISTRIBUTIONS ===
# Fedora/RHEL: sudo dnf install python3-pip python3-devel portaudio-devel libsndfile ffmpeg alsa-lib-devel sqlite
# Arch Linux: sudo pacman -S python-pip portaudio libsndfile ffmpeg alsa-lib sqlite
"""

import os
import sys
import json
import sqlite3
import hashlib
import librosa
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ML imports
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

# Audio playback
try:
    import pygame
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️  pygame non disponible - lecture audio désactivée")

# Metadata extraction
try:
    from mutagen import File as MutagenFile
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False
    print("⚠️  mutagen non disponible - détection doublons par tags désactivée")


# ============================================================================
# BASE DE DONNÉES SQLite
# ============================================================================

class AudioDatabase:
    """Gestion de la base de données SQLite pour historique"""
    
    def __init__(self, db_path: str = "audio_history.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        """Crée les tables si elles n'existent pas"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT,
                file_size INTEGER,
                duration REAL,
                sample_rate INTEGER,
                clipping_ratio REAL,
                snr_db REAL,
                crackling_rate REAL,
                zero_crossing_rate REAL,
                crest_factor REAL,
                spectral_centroid REAL,
                spectral_rolloff REAL,
                quality_score REAL,
                ml_suspicion_score REAL,
                llm_suspicion_score REAL,
                defect_timestamps TEXT,
                user_label TEXT,
                user_comment TEXT,
                tags TEXT,
                is_duplicate BOOLEAN DEFAULT 0,
                duplicate_of TEXT,
                first_analyzed TIMESTAMP,
                last_analyzed TIMESTAMP,
                UNIQUE(file_path)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON audio_files(file_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_label ON audio_files(user_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON audio_files(tags)")
        
        self.conn.commit()
    
    def insert_or_update(self, data: Dict):
        """Insert ou update un fichier"""
        cursor = self.conn.cursor()
        
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = json.dumps(data['tags'])
        if 'defect_timestamps' in data and isinstance(data['defect_timestamps'], list):
            data['defect_timestamps'] = json.dumps(data['defect_timestamps'])
        
        cursor.execute("SELECT id FROM audio_files WHERE file_path = ?", (data['file_path'],))
        exists = cursor.fetchone()
        
        if exists:
            set_clause = ", ".join([f"{k} = ?" for k in data.keys() if k != 'file_path'])
            values = [v for k, v in data.items() if k != 'file_path']
            values.append(data['file_path'])
            
            cursor.execute(f"""
                UPDATE audio_files 
                SET {set_clause}, last_analyzed = CURRENT_TIMESTAMP
                WHERE file_path = ?
            """, values)
        else:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            
            cursor.execute(f"""
                INSERT INTO audio_files ({columns}, first_analyzed, last_analyzed)
                VALUES ({placeholders}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, list(data.values()))
        
        self.conn.commit()
    
    def get_file(self, file_path: str) -> Optional[Dict]:
        """Récupère un fichier par son chemin"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM audio_files WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            if result.get('tags'):
                result['tags'] = json.loads(result['tags'])
            if result.get('defect_timestamps'):
                result['defect_timestamps'] = json.loads(result['defect_timestamps'])
            return result
        return None
    
    def get_training_data(self) -> pd.DataFrame:
        """Récupère toutes les données avec label pour entraînement ML"""
        query = """
            SELECT 
                clipping_ratio, snr_db, crackling_rate, zero_crossing_rate,
                crest_factor, spectral_centroid, spectral_rolloff, quality_score,
                CASE 
                    WHEN user_label = 'defective' THEN 1
                    WHEN user_label = 'good' THEN 0
                    ELSE NULL
                END as label
            FROM audio_files
            WHERE user_label IS NOT NULL
        """
        return pd.read_sql_query(query, self.conn)
    
    def get_files_to_skip(self) -> set:
        """Retourne les fichiers à ne pas analyser"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_path FROM audio_files 
            WHERE tags LIKE '%ban%' OR user_label = 'good'
        """)
        return {row[0] for row in cursor.fetchall()}
    
    def get_statistics(self) -> Dict:
        """Statistiques globales"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN user_label = 'defective' THEN 1 ELSE 0 END) as defective,
                SUM(CASE WHEN user_label = 'good' THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN tags LIKE '%ban%' THEN 1 ELSE 0 END) as banned,
                SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) as duplicates
            FROM audio_files
        """)
        row = cursor.fetchone()
        return {
            'total': row[0],
            'defective': row[1],
            'good': row[2],
            'banned': row[3],
            'duplicates': row[4]
        }
    
    def close(self):
        self.conn.close()


# ============================================================================
# MODÈLE ML (Random Forest)
# ============================================================================

class AudioMLModel:
    """Modèle ML pour prédiction de suspicion"""
    
    def __init__(self, model_path: str = "audio_ml_model.pkl"):
        self.model_path = model_path
        self.scaler = StandardScaler()
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.is_trained = False
        self.load_model()
    
    def load_model(self):
        """Charge le modèle si disponible"""
        if os.path.exists(self.model_path):
            try:
                data = joblib.load(self.model_path)
                self.model = data['model']
                self.scaler = data['scaler']
                self.is_trained = True
                print("✓ Modèle ML chargé")
            except:
                print("⚠️  Impossible de charger le modèle ML")
    
    def save_model(self):
        """Sauvegarde le modèle"""
        joblib.dump({'model': self.model, 'scaler': self.scaler}, self.model_path)
    
    def train(self, df: pd.DataFrame):
        """Entraîne le modèle sur les données historiques"""
        if len(df) < 10:
            print("⚠️  Pas assez de données pour entraîner le ML (minimum 10)")
            return False
        
        feature_cols = ['clipping_ratio', 'snr_db', 'crackling_rate', 
                       'zero_crossing_rate', 'crest_factor', 'spectral_centroid',
                       'spectral_rolloff', 'quality_score']
        
        X = df[feature_cols].fillna(0)
        y = df['label']
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.save_model()
        
        print(f"✓ Modèle ML entraîné sur {len(df)} échantillons")
        return True
    
    def predict_suspicion(self, metrics: Dict) -> float:
        """Prédit le score de suspicion [0-1]"""
        if not self.is_trained:
            return self._cold_start_score(metrics)
        
        features = np.array([[
            metrics.get('clipping_ratio', 0),
            metrics.get('snr_db', 0),
            metrics.get('crackling_rate', 0),
            metrics.get('zero_crossing_rate', 0),
            metrics.get('crest_factor', 0),
            metrics.get('spectral_centroid', 0),
            metrics.get('spectral_rolloff', 0),
            metrics.get('quality_score', 0)
        ]])
        
        features_scaled = self.scaler.transform(features)
        proba = self.model.predict_proba(features_scaled)[0][1]
        return float(proba)
    
    def _cold_start_score(self, metrics: Dict) -> float:
        """Score de suspicion sans ML (cold start)"""
        w1, w2, w3, w4 = 0.3, 0.3, 0.2, 0.2
        
        clipping = metrics.get('clipping_ratio', 0)
        snr = metrics.get('snr_db', 15)
        crackling = metrics.get('crackling_rate', 0)
        quality = metrics.get('quality_score', 60)
        
        score = (
            w1 * clipping +
            w2 * max(0, (15 - snr) / 15) +
            w3 * min(1, crackling / 10) +
            w4 * max(0, (60 - quality) / 60)
        )
        
        return min(1.0, max(0.0, score))


# ============================================================================
# ANALYSEUR AUDIO
# ============================================================================

class AudioAnalyzer:
    """Analyse audio avec métriques et détection défauts"""
    
    def __init__(self):
        pass
    
    def calculate_hash(self, file_path: str) -> str:
        """Hash MD5 rapide (128-bit)"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None
    
    def detect_defect_timestamps(self, y: np.ndarray, sr: int) -> List[float]:
        """Détecte les timestamps des défauts audio (en secondes)"""
        timestamps = []
        
        # Détection de clipping
        clip_indices = np.where(np.abs(y) > 0.99)[0]
        if len(clip_indices) > 0:
            groups = np.split(clip_indices, np.where(np.diff(clip_indices) > sr * 0.5)[0] + 1)
            for group in groups:
                if len(group) > sr * 0.01:
                    timestamps.append(float(group[0] / sr))
        
        # Détection de craquements
        diff = np.abs(np.diff(y))
        threshold = np.std(diff) * 5
        crack_indices = np.where(diff > threshold)[0]
        
        for idx in crack_indices:
            t = float(idx / sr)
            if not any(abs(t - existing) < 0.5 for existing in timestamps):
                timestamps.append(t)
        
        return sorted(timestamps)[:10]
    
    def analyze(self, file_path: str) -> Dict:
        """Analyse complète d'un fichier"""
        result = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'file_hash': self.calculate_hash(file_path),
            'file_size': os.path.getsize(file_path),
            'tags': []
        }
        
        if result['file_size'] == 0:
            result['tags'] = ['ban', 'empty']
            result['user_label'] = 'defective'
            result['quality_score'] = 0
            result['duration'] = 0
            return result
        
        try:
            y, sr = librosa.load(file_path, sr=None, mono=True)
            duration = librosa.get_duration(y=y, sr=sr)
            
            if duration == 0:
                result['tags'] = ['ban', 'zero_duration']
                result['user_label'] = 'defective'
                result['quality_score'] = 0
                result['duration'] = 0
                return result
            
            result['duration'] = round(duration, 2)
            result['sample_rate'] = int(sr)
            result['clipping_ratio'] = float(np.sum(np.abs(y) > 0.99) / len(y))
            
            signal_power = np.mean(y ** 2)
            noise_estimate = np.median(np.abs(y))
            result['snr_db'] = float(10 * np.log10(signal_power / (noise_estimate ** 2 + 1e-10)))
            
            diff = np.diff(y)
            threshold = np.std(diff) * 3
            crackling_count = np.sum(np.abs(diff) > threshold)
            result['crackling_rate'] = float(crackling_count / len(diff) * 1000)
            
            result['zero_crossing_rate'] = float(np.mean(librosa.zero_crossings(y)))
            result['crest_factor'] = float(np.max(np.abs(y)) / (np.sqrt(np.mean(y ** 2)) + 1e-10))
            result['spectral_centroid'] = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
            result['spectral_rolloff'] = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
            
            score = 100.0
            score -= result['clipping_ratio'] * 1000
            score -= max(0, (20 - result['snr_db']) * 2)
            score -= result['crackling_rate'] * 500
            score -= max(0, (result['zero_crossing_rate'] - 0.1) * 100)
            result['quality_score'] = float(max(0, min(100, score)))
            
            result['defect_timestamps'] = self.detect_defect_timestamps(y, sr)
            
        except Exception as e:
            result['error'] = str(e)
            result['tags'].append('analysis_error')
        
        return result


# ============================================================================
# DÉTECTION DOUBLONS
# ============================================================================

class DuplicateDetector:
    """Détecte doublons par hash, nom, taille"""
    
    def __init__(self):
        self.hash_map = {}
        self.name_map = {}
        self.size_map = {}
    
    def add_file(self, data: Dict):
        """Ajoute un fichier pour détection"""
        if data.get('file_hash'):
            h = data['file_hash']
            if h not in self.hash_map:
                self.hash_map[h] = []
            self.hash_map[h].append(data['file_path'])
        
        name = data['file_name'].lower()
        if name not in self.name_map:
            self.name_map[name] = []
        self.name_map[name].append(data['file_path'])
        
        size = data.get('file_size', 0)
        if size not in self.size_map:
            self.size_map[size] = []
        self.size_map[size].append(data['file_path'])
    
    def get_duplicates(self) -> Dict:
        """Retourne les doublons détectés"""
        return {
            'by_hash': {k: v for k, v in self.hash_map.items() if len(v) > 1},
            'by_name': {k: v for k, v in self.name_map.items() if len(v) > 1},
            'by_size': {k: v for k, v in self.size_map.items() if len(v) > 1 and k > 0}
        }
    
    def mark_duplicates(self, db: AudioDatabase):
        """Marque les doublons dans la BD"""
        dups = self.get_duplicates()
        
        for hash_val, paths in dups['by_hash'].items():
            for dup_path in paths[1:]:
                file_data = db.get_file(dup_path)
                if file_data:
                    tags = file_data.get('tags', []) or []
                    if 'duplicate' not in tags:
                        tags.append('duplicate')
                    db.insert_or_update({
                        'file_path': dup_path,
                        'is_duplicate': True,
                        'duplicate_of': hash_val,
                        'tags': tags
                    })


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """Client pour LLM local (Ollama)"""
    
    def __init__(self, url: str = "http://localhost:11434/api/generate", model: str = "llama2"):
        self.url = url
        self.model = model
    
    def query(self, prompt: str, stream: bool = False) -> str:
        """Interroge le LLM"""
        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "prompt": prompt, "stream": stream},
                timeout=180
            )
            
            if stream:
                full = ""
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get('response', '')
                        print(chunk, end='', flush=True)
                        full += chunk
                print()
                return full
            else:
                return response.json().get('response', '')
        except Exception as e:
            return f"ERREUR: {e}"
    
    def select_suspicious(self, files_data: List[Dict], top_n: int, historical_stats: Dict) -> List[Tuple[int, float]]:
        """Sélectionne les fichiers suspects avec LLM"""
        
        table = "ID | Fichier | QualityScore | ML_Score | Clipping% | SNR | Crackling | Timestamps\n"
        table += "-" * 100 + "\n"
        
        for i, f in enumerate(files_data[:30], 1):
            ts = f.get('defect_timestamps', [])
            ts_str = f"{ts[0]:.1f}s" if ts else "N/A"
            table += f"{i:2d} | {f['file_name'][:20]:20s} | {f.get('quality_score', 0):5.1f} | "
            table += f"{f.get('ml_suspicion_score', 0):5.3f} | {f.get('clipping_ratio', 0)*100:5.2f} | "
            table += f"{f.get('snr_db', 0):5.1f} | {f.get('crackling_rate', 0):6.2f} | {ts_str}\n"
        
        prompt = f"""Tu es un expert en analyse audio. Voici les {min(30, len(files_data))} fichiers les plus suspects.

HISTORIQUE:
- Total analysé: {historical_stats.get('total', 0)}
- Défectueux confirmés: {historical_stats.get('defective', 0)}
- Bonne qualité: {historical_stats.get('good', 0)}

TABLEAU:
{table}

CRITÈRES (hiérarchie stricte):
1. ML_Score > 0.8 → priorité maximale
2. Clipping% > 1.0 → critique
3. SNR < 15 → très suspect
4. Quality < 50 → mauvaise qualité
5. Presence de timestamps

Sélectionne les {top_n} fichiers LES PLUS SUSPECTS.

FORMAT STRICT (aucun autre texte):
file_id:suspicion_score,file_id:suspicion_score,...

SORTIE:"""

        print("\n🤖 Consultation du LLM...")
        response = self.query(prompt, stream=False)
        
        try:
            pairs = []
            for item in response.strip().split(','):
                if ':' in item:
                    id_str, score_str = item.strip().split(':')
                    file_id = int(id_str)
                    score = float(score_str)
                    if 1 <= file_id <= len(files_data):
                        pairs.append((file_id - 1, score))
            
            return sorted(pairs, key=lambda x: x[1], reverse=True)[:top_n]
        except:
            print("⚠️  Parsing LLM échoué, utilisation du tri ML")
            sorted_files = sorted(enumerate(files_data), key=lambda x: x[1].get('ml_suspicion_score', 0), reverse=True)
            return [(i, f.get('ml_suspicion_score', 0)) for i, f in sorted_files[:top_n]]


# ============================================================================
# PLAYER AUDIO
# ============================================================================

class AudioPlayer:
    """Lecteur audio avec positionnement"""
    
    def __init__(self):
        if AUDIO_AVAILABLE:
            pygame.mixer.init()
    
    def play(self, file_path: str, start_time: float = 0):
        """Joue à partir d'un timestamp"""
        if not AUDIO_AVAILABLE:
            print("⚠️  Lecture audio indisponible")
            return
        
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(start=start_time)
            
            print(f"▶️  Lecture depuis {start_time:.1f}s - [Espace] pour arrêter")
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    def stop(self):
        if AUDIO_AVAILABLE:
            pygame.mixer.music.stop()


# ============================================================================
# WORKFLOW PRINCIPAL
# ============================================================================

def find_audio_files(root_folder: str) -> List[str]:
    """Trouve tous les fichiers audio récursivement"""
    extensions = ['.wav', '.mp3', '.flac', '.wma', '.aac', '.ogg', '.m4a']
    files = []
    
    print(f"🔍 Scan récursif: {root_folder}")
    
    for ext in extensions:
        files.extend(Path(root_folder).rglob(f'*{ext}'))
        files.extend(Path(root_folder).rglob(f'*{ext.upper()}'))
    
    return sorted(list(set([str(f) for f in files])))


def ask_file_count(total: int) -> Tuple[int, bool]:
    """Demande combien de fichiers traiter"""
    print(f"\n📊 {total} fichiers trouvés\n")
    print("Options:")
    print(f"  1. Les 100 premiers (défaut)")
    print(f"  2. Nombre personnalisé")
    print(f"  3. TOUS les fichiers ({total})")
    print(f"  4. TOUS même déjà analysés non-défectueux")
    print(f"  0. Quitter")
    
    while True:
        choice = input("\nChoix (0-4): ").strip() or '1'
        
        if choice == '0':
            exit(0)
        elif choice == '1':
            return min(100, total), False
        elif choice == '2':
            try:
                n = int(input(f"Nombre (1-{total}): "))
                if 1 <= n <= total:
                    return n, False
            except:
                print("⚠️  Nombre invalide")
        elif choice == '3':
            return total, False
        elif choice == '4':
            return total, True
        else:
            print("⚠️  Choix invalide")


def interactive_review(files: List[Dict], db: AudioDatabase, player: AudioPlayer):
    """Révision interactive des fichiers suspects"""
    print("\n" + "=" * 80)
    print("MODE RÉVISION INTERACTIVE")
    print("=" * 80)
    print("⚠️  Les fichiers marqués DÉFECTUEUX reçoivent le tag 'ban'\n")
    
    for i, file_data in enumerate(files, 1):
        print("\n" + "-" * 80)
        print(f"Fichier {i}/{len(files)}: {file_data['file_name']}")
        print("-" * 80)
        print(f"Chemin: {file_data['file_path']}")
        print(f"Quality: {file_data.get('quality_score', 0):.1f}/100 | ML: {file_data.get('ml_suspicion_score', 0):.3f}")
        print(f"Clipping: {file_data.get('clipping_ratio', 0)*100:.2f}% | SNR: {file_data.get('snr_db', 0):.1f} dB")
        
        timestamps = file_data.get('defect_timestamps', [])
        if timestamps:
            print(f"⚠️  Défauts: {', '.join([f'{t:.1f}s' for t in timestamps[:5]])}")
        
        while True:
            cmd = input("\n[E]couter | [D]éfectueux | [B]on | [S]auter | [Q]uitter: ").strip().upper()
            
            if cmd == 'E':
                if timestamps:
                    print("Timestamps:")
                    for j, t in enumerate(timestamps, 1):
                        print(f"  {j}. {t:.1f}s")
                    ts_choice = input("Timestamp (Enter=premier): ").strip()
                    start_time = timestamps[int(ts_choice)-1] if ts_choice.isdigit() else timestamps[0]
                else:
                    start_time = 0
                
                player.play(file_data['file_path'], start_time)
            
            elif cmd == 'D':
                comment = input("Commentaire: ").strip()
                tags = file_data.get('tags', []) or []
                if 'ban' not in tags:
                    tags.append('ban')
                
                db.insert_or_update({
                    'file_path': file_data['file_path'],
                    'user_label': 'defective',
                    'user_comment': comment,
                    'tags': tags
                })
                print("✅ Marqué DÉFECTUEUX + tag 'ban'")
                break
            
            elif cmd == 'B':
                comment = input("Commentaire: ").strip()
                db.insert_or_update({
                    'file_path': file_data['file_path'],
                    'user_label': 'good',
                    'user_comment': comment
                })
                print("✅ Marqué BONNE QUALITÉ")
                break
            
            elif cmd == 'S':
                print("⏭️  Sauté")
                break
            
            elif cmd == 'Q':
                return
    
    print("\n✅ Révision terminée!")
    stats = db.get_statistics()
    print(f"Stats: {stats['defective']} défectueux, {stats['good']} bons, {stats['banned']} bannis")


def main():
    """Point d'entrée principal"""
    print("=" * 80)
    print("ANALYSEUR AUDIO AVANCÉ - ML + LLM + BASE DE DONNÉES")
    print("=" * 80)
    
    db = AudioDatabase()
    ml_model = AudioMLModel()
    analyzer = AudioAnalyzer()
    llm = LLMClient()
    player = AudioPlayer()
    
    print("\n📁 Configuration")
    folder = input("Dossier (défaut: ./audio_samples): ").strip() or "./audio_samples"
    
    if not os.path.exists(folder):
        if input("Créer? (o/n): ").lower() == 'o':
            os.makedirs(folder)
            print("✓ Créé. Ajoutez des fichiers et relancez.")
        return
    
    all_files = find_audio_files(folder)
    if not all_files:
        print("⚠️  Aucun fichier audio")
        return
    
    print("\n🤖 Vérification ML...")
training_data = db.get_training_data()
if len(training_data) >= 10:
    ml_model.train(training_data)
else:
    print(f"⚠️  Données: {len(training_data)}/10 - Mode cold start")

file_count, force_reanalyze = ask_file_count(len(all_files))

if not force_reanalyze:
    skip_files = db.get_files_to_skip()
    filtered = [f for f in all_files if f not in skip_files]
    excluded = len(all_files) - len(filtered)
    
    if excluded > 0:
        print(f"\n⛔ {excluded} fichiers exclus")
    
    files_to_analyze = filtered[:file_count]
else:
    files_to_analyze = all_files[:file_count]
    print("\n⚠️  Mode forcé")

if not files_to_analyze:
    print("⚠️  Aucun fichier")
    return

print(f"\n🔍 Analyse de {len(files_to_analyze)} fichiers...")
results = []

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(analyzer.analyze, f): f for f in files_to_analyze}
    
    completed = 0
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        completed += 1
        
        if completed % 10 == 0 or completed == len(files_to_analyze):
            print(f"   {completed}/{len(files_to_analyze)}", end='\r')

print(f"\n✓ Analyse terminée")

print("\n💾 Sauvegarde + ML...")
for result in results:
    if 'error' not in result:
        result['ml_suspicion_score'] = ml_model.predict_suspicion(result)
        db.insert_or_update(result)

print("\n🔍 Doublons...")
dup_detector = DuplicateDetector()
for r in results:
    dup_detector.add_file(r)

dup_detector.mark_duplicates(db)
duplicates = dup_detector.get_duplicates()

print(f"   Hash: {len(duplicates['by_hash'])} groupes")
print(f"   Nom: {len(duplicates['by_name'])} groupes")
print(f"   Taille: {len(duplicates['by_size'])} groupes")

valid = [r for r in results if 'ban' not in r.get('tags', [])]
banned = [r for r in results if 'ban' in r.get('tags', [])]

if banned:
    print(f"\n⛔ {len(banned)} auto-bannis")

if not valid:
    print("\n⚠️  Aucun fichier valide")
    return

valid_sorted = sorted(valid, key=lambda x: x.get('ml_suspicion_score', 0), reverse=True)

print("\n🤖 Test LLM...")
test = llm.query("Réponds 'OK'")
if "ERREUR" in test or "OK" not in test.upper():
    print("⚠️  LLM indisponible")
    top_n = int(input("Fichiers à réviser (10): ") or "10")
    suspicious = valid_sorted[:top_n]
else:
    print("✓ LLM OK")
    top_n = int(input("Fichiers à réviser (10): ") or "10")
    
    stats = db.get_statistics()
    llm_selection = llm.select_suspicious(valid_sorted, top_n, stats)
    
    suspicious = []
    for idx, llm_score in llm_selection:
        file_data = valid_sorted[idx].copy()
        file_data['llm_suspicion_score'] = llm_score
        suspicious.append(file_data)

print("\n" + "=" * 80)
print("FICHIERS SUSPECTS")
print("=" * 80)

for i, f in enumerate(suspicious, 1):
    print(f"\n{i}. {f['file_name']}")
    print(f"   Q: {f.get('quality_score', 0):.1f} | ML: {f.get('ml_suspicion_score', 0):.3f} | LLM: {f.get('llm_suspicion_score', 0):.3f}")
    print(f"   Clip: {f.get('clipping_ratio', 0)*100:.2f}% | SNR: {f.get('snr_db', 0):.1f}dB")
    if f.get('defect_timestamps'):
        print(f"   ⚠️  Défauts: {', '.join([f'{t:.1f}s' for t in f['defect_timestamps'][:3]])}")

if input("\n\nRévision interactive? (o/n): ").lower() == 'o':
    interactive_review(suspicious, db, player)

print("\n🔄 Réentraînement ML...")
training_data = db.get_training_data()
if len(training_data) >= 10:
    ml_model.train(training_data)
    print("✓ Modèle ML mis à jour")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"analysis_{timestamp}.json"

with open(output_file, 'w') as f:
    json.dump({
        'date': timestamp,
        'folder': folder,
        'total_analyzed': len(results),
        'banned': len(banned),
        'suspicious': suspicious,
        'statistics': db.get_statistics(),
        'duplicates': {
            'by_hash': len(duplicates['by_hash']),
            'by_name': len(duplicates['by_name']),
            'by_size': len(duplicates['by_size'])
        }
    }, f, indent=2)

print(f"\n💾 Rapport: {output_file}")
print(f"💾 BD: {db.db_path}")

stats = db.get_statistics()
print(f"\n📊 STATISTIQUES:")
print(f"   Total: {stats['total']}")
print(f"   Défectueux: {stats['defective']}")
print(f"   Bons: {stats['good']}")
print(f"   Bannis: {stats['banned']}")
print(f"   Doublons: {stats['duplicates']}")

db.close()
print("\n✅ Terminé!")
if name == "main":
main()
