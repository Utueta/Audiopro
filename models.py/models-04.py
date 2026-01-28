#"""
# Audiopro v0.3.1
# - Handles immutable data contracts for cross-layer communication and persistence.
#"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Primary Data Contract v0.3.1.

    Tracks deterministic DSP telemetry, analysis provenance, and arbitration outcomes.
    """
    # Identification (Blake2b hex)
    file_hash: str
    file_name: str
    file_path: str

    # DSP Metrics
    snr_value: float
    clipping_count: int
    suspicion_score: float

    # Metadata & Provenance (SR, STFT profile, hashing I/O telemetry, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Loading strategy provenance (compliance)
    was_segmented: bool = False

    # Intelligence & Arbitration
    ml_classification: str = "PENDING"
    ml_confidence: float = 0.0
    llm_verdict: Optional[str] = None
    llm_justification: Optional[str] = None

    # Arbitration status channel (stable string enum)
    arbitration_status: str = "LOCAL_ONLY"  # LOCAL_ONLY, AI_ARBITRATED, AI_FAILED
    llm_involved: bool = False

    # Persistence timestamp (UTC)
    timestamp: datetime = field(default_factory=datetime.utcnow)
