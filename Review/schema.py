"""Database schema definitions for Audiopro v01[cite: 7]."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE,
    file_name TEXT,
    file_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    snr_value REAL,
    clipping_count INTEGER,
    suspicion_score REAL,
    ml_classification TEXT
);
CREATE INDEX IF NOT EXISTS idx_file_hash ON analysis_results(file_hash);
"""
