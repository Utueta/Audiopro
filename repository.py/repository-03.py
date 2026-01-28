"""
Audiopro SQLite Repository v0.3.1
- Infrastructure: Data Storage via WAL Mode.
- v0.3.1: Enforces storage of LLM arbitration results and forensic traces.
"""

import sqlite3
import logging
from datetime import datetime
from core.models import AnalysisResult

logger = logging.getLogger("system.persistence")

class AnalysisResultStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Initializes v0.3.1 schema if not exists."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    file_hash TEXT PRIMARY KEY,
                    file_name TEXT,
                    file_path TEXT,
                    snr_value REAL,
                    clipping_count INTEGER,
                    suspicion_score REAL,
                    ml_classification TEXT,
                    ml_confidence REAL,
                    llm_verdict TEXT,
                    llm_justification TEXT,
                    arbitration_status TEXT,
                    timestamp DATETIME
                )
            """)
            conn.commit()

    def record_result(self, result: AnalysisResult):
        """Persists a full AnalysisResult contract into the learning vault."""
        query = """
            INSERT OR REPLACE INTO analysis_results (
                file_hash, file_name, file_path, snr_value, clipping_count,
                suspicion_score, ml_classification, ml_confidence,
                llm_verdict, llm_justification, arbitration_status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            result.file_hash, result.file_name, result.file_path,
            result.snr_value, result.clipping_count, result.suspicion_score,
            result.ml_classification, result.ml_confidence,
            result.llm_verdict, result.llm_justification,
            result.arbitration_status, result.timestamp.isoformat()
        )
        try:
            with self._get_connection() as conn:
                conn.execute(query, params)
                conn.commit()
        except Exception as e:
            logger.error(f"Database write failure: {e}")
