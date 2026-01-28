"""
Audiopro v0.3.1
Handles the management of system-level Python dependencies.
"""

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
    ml_classification TEXT,
    llm_verdict TEXT,
    llm_justification TEXT,
    arbitration_status TEXT DEFAULT 'LOCAL_ONLY'
);
CREATE INDEX IF NOT EXISTS idx_file_hash ON analysis_results(file_hash);
"""
