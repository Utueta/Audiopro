"""
Audiopro Random Forest Brain v0.3.1
- Implements MLModelInterface for deterministic classification.
- Handles feature vector normalization via Z-Score Scaler (v0.3).
- Logic: Returns (Verdict, Confidence) to the System Manager.
"""

import joblib
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger("system.brain.rf")

class AudioBrain:
    def __init__(self, model_path: str = None, scaler_path: str = None):
        self.model = None
        self.scaler = None
        
        if model_path and scaler_path:
            self.load_artifacts(model_path, scaler_path)

    def load_artifacts(self, model_path: str, scaler_path: str):
        """Loads the RF classifier and its corresponding Z-Score scaler."""
        try:
            if Path(model_path).exists() and Path(scaler_path).exists():
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                logger.info("Brain v0.3.1: Artifacts loaded successfully.")
            else:
                logger.warning("Brain artifacts missing. Running in uncalibrated mode.")
        except Exception as e:
            logger.error(f"Failed to load Brain artifacts: {e}")

    def classify(self, features: dict) -> tuple[str, float]:
        """
        Predicts if audio is CLEAN or CORRUPT based on DSP features.
        Input: dict containing 'snr', 'clipping', and 'suspicion_score'.
        """
        if not self.model or not self.scaler:
            return "UNKNOWN", 0.0

        # Vectorize inputs in the order defined during training
        # [SNR, Clipping, Suspicion]
        vec = np.array([[
            features.get("snr", 0.0),
            features.get("clipping", 0),
            features.get("suspicion_score", 0.0)
        ]])

        try:
            scaled_vec = self.scaler.transform(vec)
            prediction = self.model.predict(scaled_vec)[0]
            probabilities = self.model.predict_proba(scaled_vec)[0]
            
            verdict = "CLEAN" if prediction == 1 else "CORRUPT"
            confidence = float(np.max(probabilities))
            
            return verdict, confidence
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return "ERROR", 0.0
