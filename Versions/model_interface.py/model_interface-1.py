"""
Protocol definition for ML models.
Enables testing with mocks and future model swapping without changes to manager.py
"""
from typing import Protocol, Dict
from ..models import DSPAnalysis, SpectralAnalysis, MLClassification


class AudioQualityModel(Protocol):
    """
    Interface for audio quality classification models.
    Python Protocol provides type checking without runtime overhead.
    """
    
    def predict(
        self, 
        dsp: DSPAnalysis, 
        spectral: SpectralAnalysis
    ) -> MLClassification:
        """
        Predict audio quality from DSP features.
        
        Args:
            dsp: Time domain analysis results
            spectral: Frequency domain analysis results
            
        Returns:
            Classification with confidence and feature importance
        """
        ...
    
    def get_model_info(self) -> Dict[str, str]:
        """Return model version and metadata."""
        ...
    
    def is_loaded(self) -> bool:
        """Check if model weights are loaded."""
        ...
