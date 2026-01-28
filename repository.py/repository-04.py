#"""
# Audiopro v0.3.1
# - Handles thread-scoped SQLite persistence (WAL) for analysis results.
#"""

import sqlite3
import logging
from datetime import datetime
from core.models import AnalysisResult
from persistence.schema import SCHEMA


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
        import json
        from datetime import datetime

        query = """
            INSERT OR REPLACE INTO analysis_results (
                file_hash, file_name, file_path,
                snr_value, clipping_count, suspicion_score,
                was_segmented,
                ml_classification, ml_confidence,
                llm_verdict, llm_justification, llm_involved,
                arbitration_status,
                metadata_json, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        ts = getattr(result, "timestamp", None)
        if ts is None:
            ts = datetime.utcnow()

        metadata = getattr(result, "metadata", {}) or {}
        metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

        params = (
            result.file_hash, result.file_name, result.file_path,
            float(getattr(result, "snr_value", 0.0)),
            int(getattr(result, "clipping_count", 0)),
            float(getattr(result, "suspicion_score", 0.0)),
            1 if bool(getattr(result, "was_segmented", False)) else 0,
            str(getattr(result, "ml_classification", "")) or None,
            float(getattr(result, "ml_confidence", 0.0)),
            str(getattr(result, "llm_verdict", "")) or None,
            str(getattr(result, "llm_justification", "")) or None,
            1 if bool(getattr(result, "llm_involved", False)) else 0,
            str(getattr(result, "arbitration_status", "LOCAL_ONLY")) or "LOCAL_ONLY",
            metadata_json,
            ts.isoformat()
        )

        try:
            with self._get_connection() as conn:
                conn.execute(query, params)
                conn.commit()
        except Exception as e:
            logger.error(f"Database write failure: {e}")



    def wal_size_bytes(self) -> int:
        """Returns current WAL file size in bytes for monitoring."""
        try:
            import os
            return int(os.path.getsize(self.db_path + "-wal"))
        except OSError:
            return 0
