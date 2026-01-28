"""
Audiopro Time-Domain DSP v0.3.1
- Handles high-precision feature extraction for SNR and Clipping.
- v0.3.1: Implements Suspicion Score aggregation for Sentinel triage.
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

def calculate_suspicion_score(snr: float, clipping_count: int, weights: dict) -> float:
    """
    Aggregates DSP metrics into a normalized [0.0 - 1.0] score.
    Used by the Manager to trigger LLM Arbitration.
    """
    # Normalize SNR (Higher SNR = Lower Suspicion)
    # Range 0-60dB mapped to 1.0-0.0
    snr_norm = 1.0 - (np.clip(snr, 0, 60) / 60.0)
    
    # Normalize Clipping (Higher Clipping = Higher Suspicion)
    # Threshold at 500 samples for max suspicion
    clip_norm = np.clip(clipping_count / 500.0, 0, 1.0)
    
    score = (snr_norm * weights.get("snr", 0.6)) + (clip_norm * weights.get("clipping", 0.4))
    return float(np.clip(score, 0.0, 1.0))
