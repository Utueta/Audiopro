"""
Audiopro Data Contracts v0.2.5
- Defines immutable models for cross-layer communication.
- Facilitates structured telemetry and analysis persistence.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass(frozen=True)
class AnalysisResult:
    """
    The primary data contract emitted by the DSP Pipeline.
    Encapsulates time-domain, frequency-domain, and metadata features.
    """
    # Traceability & Identification
    file_hash: str [cite: 1]
    file_name: str [cite: 1]
    file_path: str [cite: 1]
    timestamp: datetime = field(default_factory=datetime.now)

    # DSP Metrics (Objective)
    snr_value: float [cite: 2]
    clipping_count: int [cite: 2]
    suspicion_score: float [cite: 2]
    
    # Metadata (Header Claims)
    metadata: Dict[str, Any] = field(default_factory=dict) [cite: 2]

    # Intelligence (Derived)
    ml_classification: str = "PENDING" [cite: 2]
    ml_confidence: float = 0.0

@dataclass(frozen=True)
class ClassificationResult:
    """
    Contract for Machine Learning Brain outputs.
    Separates the classification label from the raw DSP features.
    """
    label: str  # e.g., "CLEAN", "CORRUPT", "SUSPICIOUS" 
    confidence: float
    model_version: str
    feature_vector: tuple  # The exact numeric input used for inference
