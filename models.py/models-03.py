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

    Tracks forensic telemetry and analysis provenance. Designed to be stable over time.
    """
    # Identification
    file_hash: str
    file_name: str
    file_path: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # DSP Metrics
    snr_value: float = 0.0
    clipping_count: int = 0
    suspicion_score: float = 0.0

    # Metadata & Provenance
    metadata: Dict[str, Any] = field(default_factory=dict)
    was_segmented: bool = False  # Identifies if stratified sampling was used

    # Intelligence & Arbitration
    ml_classification: str = "PENDING"
    ml_confidence: float = 0.0

    llm_verdict: Optional[str] = None
    llm_justification: Optional[str] = None
    llm_involved: bool = False

    arbitration_status: str = "LOCAL_ONLY"
