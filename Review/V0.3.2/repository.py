"""
Audiopro Audit Repository v0.3.1
- Role: Persistence layer for the ML Feedback Loop.
- Logic: Stores AI guesses and Human truths for model evolution.
- Feature: Enables WAL Mode for concurrent script access.
"""

import sqlite3
import logging

class AuditRepository:
    def __init__(self, db_path="database/audiopro_v03.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # PRAGMA journal_mode=WAL allows concurrent read/writes
            # Crucial for allowing app.py and retrain_model.py to run together
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    file_hash TEXT PRIMARY KEY,
                    file_name TEXT,
                    file_path TEXT,
                    snr REAL,
                    clipping INTEGER,
                    ai_suspicion REAL,
                    ai_verdict TEXT,
                    final_verdict TEXT,
                    processed_for_training INTEGER DEFAULT 0
                )
            """)

    def save_audit(self, res: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO audits 
                (file_hash, file_name, file_path, snr, clipping, ai_suspicion, ai_verdict)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (res['hash'], res['name'], res['path'], res['snr'], 
                  res['clipping'], res['suspicion'], res['verdict']))

    def update_final_verdict(self, file_hash: str, verdict: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE audits 
                SET final_verdict = ?, processed_for_training = 0 
                WHERE file_hash = ?
            """, (verdict, file_hash))
