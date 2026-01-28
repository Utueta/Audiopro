#"""
# Audiopro v0.3.1
# - Handles SQLite schema definition for analysis result persistence.
#"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis_results (
    file_hash TEXT PRIMARY KEY,
    file_name TEXT,
    file_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    snr_value REAL,
    clipping_count INTEGER,
    suspicion_score REAL,

    was_segmented INTEGER DEFAULT 0,


    ml_classification TEXT,
    ml_confidence REAL,

    llm_verdict TEXT,
    llm_justification TEXT,
    llm_involved INTEGER DEFAULT 0,

    arbitration_status TEXT,


    -- JSON text blob for deterministic feature provenance and metadata (SR, STFT profile, etc.)
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_analysis_file_hash ON analysis_results(file_hash);
"""
