import sqlite3
import os
import logging
from core.models import AnalysisResult

class AudioRepository:
    def __init__(self, db_path="database/audiopro_v01.db"):
        self.db_path = db_path
        self.logger = logging.getLogger("Audiopro.Repository")
        self._initialize_db()

    def get_connection(self):
        """Standard connection factory with Industrial WAL settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # ARCHITECTURE.md: SQLite Multi-Threaded Access Configuration
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT,
                        centroid REAL,
                        noise_floor REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except sqlite3.Error as e:
            self.logger.critical(f"Database initialization failed: {e}")

    def save_result(self, result: AnalysisResult):
        """Thread-safe write operation using the repository factory."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO analysis_history (file_path, centroid, noise_floor) VALUES (?, ?, ?)",
                    (result.path, result.centroid, result.noise_floor)
                )
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to persist result for {result.path}: {e}")
