"""
SQLite repository with connection pooling and thread safety.
Isolates SQL details from business logic.
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager
from threading import Lock

from core.models import AnalysisResult


logger = logging.getLogger(__name__)


class AnalysisRepository:
    """
    Thread-safe SQLite repository for analysis results.
    Uses WAL mode and connection-per-thread pattern.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema."""
        with self._get_connection() as conn:
            # Enable WAL mode for concurrent reads
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            # Create schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id TEXT PRIMARY KEY,
                    filepath TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT,
                    dsp_json TEXT,
                    spectral_json TEXT,
                    ml_json TEXT,
                    llm_json TEXT,
                    final_quality TEXT,
                    user_feedback TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_filepath ON analyses(filepath)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp)")
            logger.info(f"Database initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Thread-safe connection context manager."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save(self, result: AnalysisResult) -> None:
        """Save analysis result to database."""
        with self._lock, self._get_connection() as conn:
            data = result.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO analyses 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['analysis_id'],
                data['filepath'],
                data['timestamp'],
                str(data['metadata']),
                str(data['dsp']),
                str(data['spectral']),
                str(data['ml_classification']),
                str(data['llm_arbitration']),
                data['final_quality'],
                data['user_feedback']
            ))
            logger.debug(f"Saved analysis: {result.analysis_id}")
    
    def get_by_id(self, analysis_id: str) -> Optional[AnalysisResult]:
        """Retrieve analysis by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM analyses WHERE analysis_id = ?",
                (analysis_id,)
            ).fetchone()
            
            if row:
                return AnalysisResult.from_dict(dict(row))
            return None
    
    def get_by_filepath(self, filepath: Path) -> Optional[AnalysisResult]:
        """Get most recent analysis for file."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM analyses 
                WHERE filepath = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (str(filepath),)).fetchone()
            
            if row:
                return AnalysisResult.from_dict(dict(row))
            return None
    
    def get_all(self, limit: int = 100) -> List[AnalysisResult]:
        """Get recent analyses."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM analyses 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [AnalysisResult.from_dict(dict(row)) for row in rows]
    
    def update_feedback(self, analysis_id: str, feedback: str) -> None:
        """Update user feedback for incremental learning."""
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                UPDATE analyses 
                SET user_feedback = ? 
                WHERE analysis_id = ?
            """, (feedback, analysis_id))
            logger.info(f"Updated feedback for {analysis_id}")
