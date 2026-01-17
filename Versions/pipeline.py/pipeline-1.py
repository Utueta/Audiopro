import librosa
import numpy as np
import logging
from core.models import AnalysisResult

class AudioAnalyzer:
    """Stateless DSP Engine for high-precision audio auditing."""
    
    @staticmethod
    def analyze_file(file_path: str) -> AnalysisResult:
        """Memory-scoped feature extraction pipeline."""
        logger = logging.getLogger("Audiopro.Analyzer")
        try:
            # Load audio - sr=None preserves native quality for forensic accuracy
            y, sr = librosa.load(file_path, sr=None)
            
            # Feature extraction (High-precision FFT)
            stft = np.abs(librosa.stft(y))
            centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
            noise_floor = float(np.min(librosa.amplitude_to_db(stft)))
            
            # ARCHITECTURE.md compliance: Explicit buffer release to prevent memory leaks
            del y
            del stft
            
            return AnalysisResult(
                path=file_path,
                success=True,
                centroid=round(centroid, 2),
                noise_floor=round(noise_floor, 2)
            )
        except Exception as e:
            logger.error(f"DSP Failure on {file_path}: {str(e)}")
            return AnalysisResult(path=file_path, success=False, error=str(e))
