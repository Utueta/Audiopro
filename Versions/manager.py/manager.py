import os
import sqlite3
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Import des modules consolidés (Buffer Actif)
from core.analyzer.dsp import AudioAnalyzer
from core.analyzer.spectral import SpectralExpert
from core.analyzer.metadata import MetadataExpert
from core.brain.model import BrainModel
from services.llm_service import LLMArbitrator

class CentralManager:
    """
    Chef d'orchestre consolidé du projet Audiopro.
    Gère le pipeline de certification, la persistance et la traçabilité.
    """
    def __init__(self, db_path="database/inventory.db", config_path="config.json"):
        self.db_path = db_path
        self._setup_logging()
        
        # Chargement de la configuration
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.logger.warning("config.json introuvable, utilisation des seuils par défaut.")
            self.config = {"threshold_ban": 0.8, "threshold_warning": 0.5}

        # Initialisation des experts consolidés
        self.dsp_expert = AudioAnalyzer()
        self.spectral_expert = SpectralExpert()
        self.metadata_expert = MetadataExpert()
        self.brain = BrainModel()
        self.llm = LLMArbitrator()
        
        self._init_db()

    def _setup_logging(self):
        """Configuration DevSecOps : Traçabilité complète dans logs/."""
        os.makedirs("logs", exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler("logs/analysis.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("Audiopro.Manager")

    def _init_db(self):
        """Initialisation de la base de données de certification."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    hash TEXT PRIMARY KEY,
                    path TEXT,
                    filename TEXT,
                    format TEXT,
                    bitrate INTEGER,
                    is_spoofed INTEGER,
                    clipping REAL,
                    snr REAL,
                    phase_corr REAL,
                    cutoff_hz INTEGER,
                    ml_score REAL,
                    final_status TEXT,
                    timestamp DATETIME
                )
            """)
            conn.commit()

    def process_file(self, file_path):
        """
        Pipeline de certification complet (Metadata -> DSP -> Brain -> LLM).
        Plus-value : Analyse croisée pour une précision maximale.
        """
        try:
            filename = os.path.basename(file_path)
            self.logger.info(f"Analyse en cours : {filename}")

            # 1. Hachage rapide pour le cache
            f_hash = self.dsp_expert.get_fast_hash(file_path)
            cached_res = self._check_cache(f_hash)
            if cached_res:
                return cached_res

            # 2. Extraction Metadata (Validation Header)
            meta = self.metadata_expert.extract_info(file_path)
            if meta['status'] == "SPOOF_ALERT":
                self.logger.warning(f"SPOOFING DÉTECTÉ : {filename}")

            # 3. Analyse DSP & Spectrale (Signal)
            y, sr, engine = self.dsp_expert.load_audio_safely(file_path)
            dsp_res = {
                "clipping": self.dsp_expert.analyze_clipping(y),
                "snr": self.dsp_expert.analyze_snr(y),
                "phase": self.dsp_expert.analyze_phase(y)
            }
            spec_res = self.spectral_expert.detect_fake_hq(y, sr)

            # Fusion des données pour le Brain
            analysis_data = {**dsp_res, **spec_res}
            
            # 4. Inférence ML
            ml_score = self.brain.predict(analysis_data, meta)

            # 5. Décision Finale & Arbitrage LLM
            final_status = self._decide_status(ml_score, analysis_data, meta)
            
            # 6. Persistance
            self._save_result(f_hash, file_path, meta, analysis_data, ml_score, final_status)

            return {
                "status": "SUCCESS",
                "filename": filename,
                "score": ml_score,
                "verdict": final_status,
                "meta": meta,
                "analysis": analysis_data
            }

        except Exception as e:
            self.logger.error(f"Échec analyse sur {file_path}: {str(e)}")
            return {"status": "ERROR", "msg": str(e), "path": file_path}

    def _decide_status(self, ml_score, dsp, meta):
        """Logique de décision multicritère."""
        if meta['is_spoofed'] or ml_score >= self.config['threshold_ban']:
            return "BAN (Fake/Spoofed)"
        if ml_score >= self.config['threshold_warning']:
            # Appel au service LLM pour arbitrage en zone grise
            return self.llm.arbitrate(dsp, meta, ml_score)
        return "GOOD"

    def _save_result(self, f_hash, path, meta, dsp, score, status):
        """Sauvegarde étendue pour auditabilité."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO inventory 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f_hash, path, os.path.basename(path), meta['format_internal'],
                meta['bitrate'], int(meta['is_spoofed']), dsp['clipping'],
                dsp['snr'], dsp['phase_corr'], dsp['spectral_cutoff'],
                score, status, datetime.now()
            ))

    def _check_cache(self, f_hash):
        """Vérifie si le fichier a déjà été certifié."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT final_status, ml_score FROM inventory WHERE hash=?", (f_hash,))
            row = cursor.fetchone()
            if row:
                return {"status": "CACHED", "verdict": row[0], "score": row[1]}
        return None
