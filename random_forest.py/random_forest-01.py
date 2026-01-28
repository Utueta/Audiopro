"""
Audiopro v0.3.1
Handles the Random Forest classification, feature normalization (Z-Score), and deterministic heuristic fallback.
"""
import joblib
import numpy as np
import logging
from pathlib import Path
from .model_interface import ModelInterface

logger = logging.getLogger("system.brain.sentinel")

class AudioBrain(ModelInterface):
    """
    Audiopro Random Forest Brain v0.3.1
    - Implements MLModelInterface for deterministic classification
    - Handles feature vector normalization via Z-Score Scaler
    - Manages persistent weight loading from .pkl artifacts
    """
    def __init__(self, 
                 model_path: str = "core/brain/weights/random_forest.pkl",
                 scaler_path: str = "core/brain/weights/scaler_v0.3.pkl"):
        
        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        
        self.model = None
        self.scaler = None
        
        self.lower_threshold = 0.35
        self.upper_threshold = 0.75
        
        self.load_artifacts()

    def load_artifacts(self):
        """Loads model and scaler artifacts for normalized inference."""
        try:
            if self.model_path.exists():
                self.model = joblib.load(self.model_path)
            if self.scaler_path.exists():
                self.scaler = joblib.load(self.scaler_path)
            logger.info("Sentinel Brain artifacts loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load ML artifacts: {e}")

    def predict(self, features: dict) -> float:
        """
        Primary Inference: Returns raw Suspicion Score [0.0 - 1.0].
        Implements Z-Score normalization before forest projection.
        """
        if self.model and self.scaler:
            try:
                # 1. Vectorization
                raw_vec = np.array([[features['snr'], features['clipping']]])
                
                # 2. Z-Score Normalization (Compliance Merge)
                scaled_vec = self.scaler.transform(raw_vec)
                
                # 3. Probability Inference
                return float(self.model.predict_proba(scaled_vec)[0][1])
            except Exception as e:
                logger.warning(f"ML Inference failed, falling back to heuristic: {e}")
                return self._calculate_heuristic(features)
        
        return self._calculate_heuristic(features)

    def classify(self, features: dict) -> tuple[str, float]:
        """v0.3.1 Triage: Maps score to Industrial Labels."""
        score = self.predict(features)
        if score < self.lower_threshold:
            return "CLEAN", score
        if score > self.upper_threshold:
            return "CORRUPT", score
        return "SUSPICIOUS", score

    def _calculate_heuristic(self, f: dict) -> float:
        """Non-Oversimplified 60/40 Fallback (Sentinel Standard)."""
        snr_factor = max(0.0, (20.0 - f.get('snr', 20.0)) / 20.0)
        clip_factor = min(1.0, f.get('clipping', 0) / 100.0)
        return (snr_factor * 0.6) + (clip_factor * 0.4)

    def load(self, path: str):
        """Interface compliance for dynamic loading."""
        self.model = joblib.load(path)

    def save(self, path: str):
        """Persists model state."""
        if self.model:
            joblib.dump(self.model, path)
