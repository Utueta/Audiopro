"""
Audiopro Data Contracts v0.3.1
- Defines immutable models for cross-layer communication.
- v0.3.1: Added LLM Verdict and Justification for arbitration transparency.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass(frozen=True)
class AnalysisResult:
    """The primary data contract emitted by the DSP Pipeline and enriched by ML/LLM."""
    # Identification (Blake2b)
    file_hash: str
    file_name: str
    file_path: str
    timestamp: datetime = field(default_factory=datetime.now)

    # DSP Metrics
    snr_value: float
    clipping_count: int
    suspicion_score: float  # Spectral suspicion
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Intelligence & Arbitration
    ml_classification: str = "PENDING"
    ml_confidence: float = 0.0
    llm_verdict: Optional[str] = None
    llm_justification: Optional[str] = None
    arbitration_status: str = "LOCAL_ONLY"  # LOCAL_ONLY, AI_ARBITRATED, AI_FAILED
