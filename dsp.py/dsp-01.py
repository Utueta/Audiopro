"""
Audiopro Time-Domain DSP v0.2.5 [HYBRID]
- Optimized for Pipeline Orchestration
- Includes SNR, Clipping, and Phase Correlation
"""

import numpy as np
import librosa
import logging

analysis_logger = logging.getLogger("analysis")

def calculate_snr(file_path: str) -> float:
    """Estimates SNR via noise floor variance analysis."""
    try:
        y, _ = librosa.load(file_path, sr=None, mono=True)
        if len(y) == 0: return 0.0
        signal_power = np.mean(y**2)
        noise_power = np.amin(librosa.feature.rms(y=y))**2
        if noise_power <= 0: return 100.0
        return float(np.clip(10 * np.log10(signal_power / noise_power), 0, 100))
    except Exception as e:
        analysis_logger.error(f"SNR Error: {e}")
        return 0.0

def detect_clipping(file_path: str, threshold: float = 0.99) -> int:
    """Counts samples hitting digital ceiling."""
    try:
        y, _ = librosa.load(file_path, sr=None, mono=True)
        return int(np.sum(np.abs(y) >= threshold))
    except Exception as e:
        analysis_logger.error(f"Clipping Error: {e}")
        return 0

def analyze_phase(file_path: str) -> float:
    """Detects phase issues in stereo files (New Metric)."""
    try:
        y_stereo, _ = librosa.load(file_path, sr=None, mono=False)
        if y_stereo.ndim < 2: return 1.0 # Mono is perfectly correlated
        
        # Pearson correlation between Left and Right channels
        num = np.sum(y_stereo[0] * y_stereo[1])
        den = np.sqrt(np.sum(y_stereo[0]**2) * np.sum(y_stereo[1]**2))
        return float(num / den) if den != 0 else 0.0
    except:
        return 1.0
