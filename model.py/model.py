"""
Typed data contracts for inter-layer communication.
Ensures type safety and clear boundaries without architectural overhead.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass(frozen=True)
class AudioMetadata:
    """Immutable metadata extracted from audio file."""
    filepath: Path
    duration_sec: float
    sample_rate: int
    bitrate: int
    codec: str
    file_size_mb: float
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['filepath'] = str(data['filepath'])
        return data


@dataclass(frozen=True)
class DSPAnalysis:
    """Results from signal processing analysis."""
    rms_level_db: float
    peak_level_db: float
    crest_factor: float
    phase_correlation: float
    clipping_detected: bool
    dynamic_range_db: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SpectralAnalysis:
    """Results from frequency domain analysis."""
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    high_freq_cutoff_khz: float
    low_freq_energy_db: float
    mid_freq_energy_db: float
    high_freq_energy_db: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MLClassification:
    """Machine learning inference result."""
    predicted_class: str  # "excellent", "good", "acceptable", "poor"
    confidence: float     # 0.0 to 1.0
    feature_importance: dict
    model_version: str
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LLMArbitration:
    """LLM arbitration result for edge cases."""
    recommendation: str
    reasoning: str
    confidence_override: Optional[float]
    timestamp: datetime
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data


@dataclass(frozen=True)
class AnalysisResult:
    """
    Complete analysis result aggregating all subsystems.
    Single source of truth passed between layers.
    """
    # Identity
    analysis_id: str
    filepath: Path
    timestamp: datetime
    
    # Component results
    metadata: AudioMetadata
    dsp: DSPAnalysis
    spectral: SpectralAnalysis
    ml_classification: MLClassification
    llm_arbitration: Optional[LLMArbitration]
    
    # Final verdict
    final_quality: str  # "excellent", "good", "acceptable", "poor", "needs_review"
    user_feedback: Optional[str]  # For incremental learning
    
    def to_dict(self) -> dict:
        """Serialize for SQLite/JSON storage."""
        return {
            'analysis_id': self.analysis_id,
            'filepath': str(self.filepath),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata.to_dict(),
            'dsp': self.dsp.to_dict(),
            'spectral': self.spectral.to_dict(),
            'ml_classification': self.ml_classification.to_dict(),
            'llm_arbitration': self.llm_arbitration.to_dict() if self.llm_arbitration else None,
            'final_quality': self.final_quality,
            'user_feedback': self.user_feedback
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AnalysisResult':
        """Deserialize from storage."""
        # Implementation details...
        pass
