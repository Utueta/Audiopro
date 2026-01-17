import os
import sqlite3
import logging
from core.analyzer.dsp import AudioAnalyzer
from core.analyzer.spectral import SpectralExpert
from core.brain.model import BrainModel
from services.llm_service import LLMArbitrator

class CentralManager:
    def __init__(self, db_path, model_path, config):
        self.config = config
        self.db_path = db_path
        
        # Initialisation des composants techniques
        self.dsp_engine = AudioAnalyzer()
        self.spectral_engine = SpectralExpert()
        self.brain = BrainModel(model_path)
        self.llm = LLMArbitrator()
        
        # Initialisation de la base de données SQLite
        self._init_db()
        self.logger = logging.getLogger("AudioExpert.Manager")

    def _init_db(self):
        """Crée la structure de la base de données si elle n'existe pas."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;") 
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                hash TEXT PRIMARY KEY,
                path TEXT,
                clipping REAL,
                snr REAL,
                phase_corr REAL,
                fake_hq_score REAL,
                ml_score REAL,
                llm_verdict TEXT,
                status TEXT DEFAULT 'PENDING'
            )
        """)
        self.conn.commit()

    def process_file(self, file_path):
        """
        Analyse complète d'un fichier audio synchronisée avec l'interface.
        """
        try:
            # 0. Identification
            f_hash = self.dsp_engine.get_fast_hash(file_path)

            # 1. Vérification du Cache
            cursor = self.conn.cursor()
            cursor.execute("SELECT status, ml_score FROM inventory WHERE hash=?", (f_hash,))
            cached = cursor.fetchone()
            if cached and cached[0] in ['GOOD', 'BAN']:
                return {
                    "status": "SKIPPED", 
                    "hash": f_hash, 
                    "path": file_path, 
                    "engine": "Cache (SQL)",
                    "ml_score": cached[1],
                    "final_decision": cached[0]
                }

            # 2. Chargement de l'audio (Retourne 3 valeurs : y, sr, engine_name)
            y, sr, engine_used = self.dsp_engine.load_audio_safely(file_path)
            
            # 3. Analyse Technique (DSP + Spectral)
            spectral_res = self.spectral_engine.detect_fake_hq(y, sr)
            
            dsp_data = {
                "clipping": self.dsp_engine.analyze_clipping(y),
                "phase": self.dsp_engine.analyze_phase(y),
                "snr": self.dsp_engine.analyze_snr(y),
                "fake_hq": spectral_res.get('fake_hq_probability', 0),
                "cutoff": spectral_res.get('spectral_cutoff', 0)
            }

            # 4. Prédiction Intelligence Artificielle
            ml_score = self.brain.predict(dsp_data)
            llm_data = None

            # 5. Arbitrage LLM pour la "Zone Grise"
            if 0.4 <= ml_score <= 0.7:
                self.logger.info(f"Arbitrage LLM requis pour {file_path}")
                llm_data = self.llm.get_verdict(file_path, dsp_data, ml_score)
                final_status = llm_data['verdict'] if llm_data['confidence'] > 0.8 else 'NEEDS_REVIEW'
            else:
                final_status = 'BAN' if ml_score > 0.7 else 'GOOD'

            # 6. Archivage en Base de Données
            self._save_to_db(f_hash, file_path, dsp_data, ml_score, llm_data, final_status)

            # 7. Retour pour l'UI (Clés harmonisées)
            return {
                "status": "SUCCESS",
                "hash": f_hash,
                "path": file_path,
                "engine": engine_used,
                "dsp": dsp_data,
                "ml_score": ml_score,  # Clé ajustée pour correspondre à view.py
                "llm_analysis": llm_data,
                "final_decision": final_status
            }

        except Exception as e:
            self.logger.error(f"Erreur sur {file_path} : {str(e)}")
            return {
                "status": "ERROR", 
                "path": file_path, 
                "engine": "FAILED",
                "msg": str(e)
            }

    def _save_to_db(self, f_hash, path, dsp, score, llm, status):
        """Enregistre les résultats de manière persistante."""
        llm_reason = llm['reason'] if llm else None
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO inventory 
                (hash, path, clipping, snr, phase_corr, fake_hq_score, ml_score, llm_verdict, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f_hash, path, dsp['clipping'], dsp['snr'], dsp['phase'], dsp['fake_hq'], score, llm_reason, status))
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Erreur SQL : {e}")
