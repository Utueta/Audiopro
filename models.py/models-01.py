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
    """Primary immutable data contract emitted by DSP and enriched by ML/LLM."""
    # Identification (Blake2b 128-bit hex)
    file_hash: str
    file_name: str
    file_path: str

    # DSP Metrics
    snr_value: float
    clipping_count: int
    suspicion_score: float

    # Metadata and provenance (container facts, SR, STFT profile, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Intelligence & Arbitration
    ml_classification: str = "PENDING"
    ml_confidence: float = 0.0
    llm_verdict: Optional[str] = None
    llm_justification: Optional[str] = None
    llm_involved: bool = False

    # Persistence timestamp (UTC ISO)
    timestamp: datetime = field(default_factory=datetime.utcnow)
