"""
Audiopro v0.3.1
Handles thread-safe SQLite persistence using WAL mode for the learning vault.
"""
import sqlite3
from pathlib import Path

class Repository:
    def __init__(self, db_path: str = "database/audiopro_v03.db"):
        self.db_path = db_path
        self._initialize_vault()

    def _initialize_vault(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY,
                    file_hash TEXT,
                    verdict TEXT,
                    score REAL,
                    expert_validated INTEGER DEFAULT 0
                )
            """)
