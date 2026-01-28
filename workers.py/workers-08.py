"""
Audiopro Random Forest Brain v0.2.5
- Implements MLModelInterface for deterministic classification
- Handles feature vector normalization via Z-Score Scaler
- Manages persistent weight loading from .pkl artifacts
"""

import os
import logging
import hashlib
import pickle
import numpy as np
from typing import Dict, Any, Tuple, Union
from abc import ABC, abstractmethod
from mutagen import File

# Configuration & Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Audiopro.System")

# --- Interfaces ---

class MLModelInterface(ABC):
    """Standard interface for deterministic classification models."""
    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def load_weights(self, path: str) -> None:
        pass

# --- Core Logic ---

class MetadataExpert:
    """
    Consolidated Engineering Board Edition.
    Handles structural file auditing and feature vector extraction.
    """
    def __init__(self):
        self.lossless_extensions = {'.FLAC', '.WAV', '.AIFF', '.WV', '.ALAC'}
        self.supported_extensions = {'.MP3', '.FLAC', '.WAV', '.M4A', '.OGG', '.AIFF'}

    def get_fast_hash(self, file_path: str) -> str:
        """MD5 on initial 8MB chunk for performance-ratio optimized deduplication."""
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"
        
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192 * 1024)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            logger.error(f"IO Failure hashing {file_path}: {e}")
            return hashlib.md5(file_path.encode()).hexdigest()

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """Extracts technical specs and executes security cross-checks."""
        if not os.path.exists(file_path):
            return self._generate_error_state("MISSING")

        file_ext = os.path.splitext(file_path)[1].upper()
        
        try:
            stats = os.stat(file_path)
            audio = File(file_path, easy=True)
            
            if audio and audio.info:
                info = audio.info
                actual_format = type(audio).__name__.replace('Easy', '').replace('FileType', '')
                is_spoofed = self._verify_integrity(file_path, audio, info)
                
                return {
                    "hash": self.get_fast_hash(file_path),
                    "format_internal": actual_format,
                    "format_ext": file_ext,
                    "filesize_mb": round(stats.st_size / (1024 * 1024), 2),
                    "bitrate": self._get_bitrate_kbps(info),
                    "sample_rate": getattr(info, 'sample_rate', 0),
                    "channels": getattr(info, 'channels', 0),
                    "bits_per_sample": getattr(info, 'bits_per_sample', 0),
                    "is_spoofed": is_spoofed,
                    "is_lossless": (file_ext in self.lossless_extensions and "MP3" not in actual_format.upper()),
                    "status": "VALIDATED" if not is_spoofed else "SPOOF_ALERT"
                }
            return self._generate_error_state("CORRUPT_HEADER")

        except Exception as e:
            logger.error(f"Metadata architecture failure on {file_path}: {e}")
            return self._generate_error_state("CRASHED")

    def _get_bitrate_kbps(self, info) -> int:
        br = getattr(info, 'bitrate', 0)
        return br // 1000 if br else 0

    def _verify_integrity(self, path: str, audio_obj: Any, info: Any) -> bool:
        ext = os.path.splitext(path)[1].lower()
        internal_fmt = type(audio_obj).__name__.upper()

        if ext == '.flac' and 'FLAC' not in internal_fmt:
            return True
        if ext == '.flac':
            br = getattr(info, 'bitrate', 500000)
            if br != 0 and br < 128000:
                return True
        return False

    def _generate_error_state(self, reason: str) -> Dict[str, Any]:
        return {"format_internal": "ERROR", "filesize_mb": 0, "is_spoofed": True, "status": reason}

class RandomForestClassifier(MLModelInterface):
    """
    Consolidated Random Forest implementation.
    Integrates feature normalization and persistent weight management.
    """
    def __init__(self, n_estimators=100):
        self.model = None
        self.scaler_mean = None
        self.scaler_std = None

    def load_weights(self, artifact_path: str):
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Weight file missing: {artifact_path}")
            
        try:
            with open(artifact_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler_mean = data['scaler_mean']
                self.scaler_std = data['scaler_std']
            logger.info("Weights and scaler parameters loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load weights: {e}")
            raise

    def _normalize(self, features: np.ndarray) -> np.ndarray:
        if self.scaler_mean is None or self.scaler_std is None:
            return features
        return (features - self.scaler_mean) / (self.scaler_std + 1e-9)

    def predict(self, features: Union[list, np.ndarray]) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model weights must be loaded before prediction.")
            
        feat_array = np.array(features)
        if feat_array.ndim == 1:
            feat_array = feat_array.reshape(1, -1)
            
        normalized_features = self._normalize(feat_array)
        return self.model.predict(normalized_features)

if __name__ == "__main__":
    # ERB Industrial Integration Test
    expert = MetadataExpert()
    brain = RandomForestClassifier()
    print("Audiopro Random Forest Brain v0.2.5 [READY]")
