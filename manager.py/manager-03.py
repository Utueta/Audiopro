import os
import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Core Subsystems
from core.analyzer.dsp import AudioAnalyzer
from core.analyzer.spectral import SpectralExpert
from core.brain.model import BrainModel
from services.llm_service import LLMArbitrator

logger = logging.getLogger("Audiopro.Manager")

class CentralManager:
    """
    Audiopro Random Forest Brain v0.2.5 - Central Manager
    Orchestrates the analysis pipeline with Industrial-grade safety.
    """
    def __init__(self, db_path: str, model_path: str, config_path: str = "config.json"):
        self.db_path = db_path
        self.model_path = model_path
        
        # Load Configuration
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception:
            logger.warning("Config missing; using industrial defaults.")
            self.config = {"threshold_ban": 0.8, "llm_threshold": 0.65}

        # Component Initialization
        self.dsp_engine = AudioAnalyzer()
        self.spectral_engine = SpectralExpert()
        self.brain = BrainModel(model_path)
        self.llm = LLMArbitrator()
        
        self._init_db()

    def _init_db(self):
        """Initializes SQLite with WAL mode for concurrent threading safety."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    hash TEXT PRIMARY KEY,
                    path TEXT,
                    clipping REAL,
                    snr REAL,
                    ml_score REAL,
                    llm_verdict TEXT,
                    status TEXT,
                    timestamp DATETIME
                )
            """)

    def process_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous pipeline executed by AnalysisWorker threads.
        """
        try:
            # 1. Deduplication (Cache Check)
            f_hash = self.dsp_engine.get_fast_hash(file_path)
            cached = self._check_cache(f_hash)
            if cached: return cached

            # 2. DSP & Feature Extraction (Forced Resampling)
            # y: waveform, sr: sample_rate
            y, sr, engine = self.dsp_engine.load_audio_safely(file_path)
            dsp_features = self.dsp_engine.analyze_all(y, sr)
            spectral_res = self.spectral_engine.detect_fake_hq(y, sr)

            # 3. ML Inference (Random Forest Brain)
            # Merges DSP + Spectral into a Z-Score normalized vector
            ml_score = self.brain.predict(dsp_features, spectral_res)

            # 4. LLM Arbitrage (Conditional)
            llm_data = {"reason": "ML Confident", "verdict": None}
            if ml_score > self.config["llm_threshold"] and ml_score < self.config["threshold_ban"]:
                llm_data = self.llm.arbitrate(dsp_features, spectral_res, ml_score)

            # 5. Final Decision Logic
            status = self._decide_status(ml_score, llm_data)

            # 6. Persistence
            self._save_to_db(f_hash, file_path, dsp_features, ml_score, llm_data, status)

            return {
                "status": "SUCCESS",
                "hash": f_hash,
                "path": file_path,
                "ml_score": ml_score,
                "llm_analysis": llm_data,
                "final_decision": status
            }

        except Exception as e:
            logger.error(f"Pipeline failure on {file_path}: {str(e)}")
            raise e

    def _check_cache(self, f_hash: str):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT status, ml_score FROM inventory WHERE hash=?", (f_hash,)).fetchone()
            if row:
                return {"status": "SKIPPED", "final_decision": row[0], "ml_score": row[1]}
        return None

    def _decide_status(self, score: float, llm: dict) -> str:
        if llm["verdict"]: return llm["verdict"]
        return "BAN" if score >= self.config["threshold_ban"] else "GOOD"

    def _save_to_db(self, f_hash, path, dsp, score, llm, status):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO inventory 
                (hash, path, clipping, snr, ml_score, llm_verdict, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (f_hash, path, dsp['clipping'], dsp['snr'], score, llm['reason'], status, datetime.now()))
