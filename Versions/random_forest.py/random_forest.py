"""
Random Forest implementation of AudioQualityModel protocol.
"""
import joblib
from pathlib import Path
import logging
from typing import Dict

from .model_interface import AudioQualityModel
from ..models import DSPAnalysis, SpectralAnalysis, MLClassification


logger = logging.getLogger(__name__)


class RandomForestClassifier:
    """Random Forest model for audio quality prediction."""
    
    def __init__(self, weights_path: Path):
        self.weights_path = weights_path
        self.model = None
        self.scaler = None
        self._load_weights()
    
    def _load_weights(self):
        """Load model and scaler from disk."""
        try:
            model_file = self.weights_path / "audio_expert_rf.joblib"
            scaler_file = self.weights_path / "scaler.pkl"
            
            self.model = joblib.load(model_file)
            self.scaler = joblib.load(scaler_file)
            logger.info(f"Model loaded: {model_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model initialization failed: {e}") from e
    
    def predict(self, dsp: DSPAnalysis, spectral: SpectralAnalysis) -> MLClassification:
        """Implement protocol method."""
        if not self.is_loaded():
            raise RuntimeError("Model not loaded")
        
        # Feature engineering
        features = self._extract_features(dsp, spectral)
        features_scaled = self.scaler.transform([features])
        
        # Inference
        prediction = self.model.predict(features_scaled)[0]
        confidence = self.model.predict_proba(features_scaled).max()
        importance = dict(zip(
            self._get_feature_names(),
            self.model.feature_importances_
        ))
        
        return MLClassification(
            predicted_class=prediction,
            confidence=float(confidence),
            feature_importance=importance,
            model_version="v1.0_rf"
        )
    
    def _extract_features(self, dsp: DSPAnalysis, spectral: SpectralAnalysis) -> list:
        """Convert analysis results to feature vector."""
        return [
            dsp.rms_level_db,
            dsp.dynamic_range_db,
            dsp.crest_factor,
            dsp.phase_correlation,
            1.0 if dsp.clipping_detected else 0.0,
            spectral.spectral_centroid_hz,
            spectral.high_freq_cutoff_khz,
            spectral.low_freq_energy_db,
            spectral.mid_freq_energy_db,
            spectral.high_freq_energy_db,
        ]
    
    def _get_feature_names(self) -> list:
        """Feature names for importance mapping."""
        return [
            'rms_level', 'dynamic_range', 'crest_factor',
            'phase_correlation', 'clipping',
            'spectral_centroid', 'freq_cutoff',
            'low_energy', 'mid_energy', 'high_energy'
        ]
    
    def get_model_info(self) -> Dict[str, str]:
        """Implement protocol method."""
        return {
            'type': 'RandomForest',
            'version': 'v1.0',
            'n_estimators': str(self.model.n_estimators) if self.model else 'N/A'
        }
    
    def is_loaded(self) -> bool:
        """Implement protocol method."""
        return self.model is not None and self.scaler is not None
