"""
Audiopro Spectral Analysis v0.3.1
- STFT-based frequency domain auditing.
- Detects artificial brickwall filters and upsampling.
- Generates suspicion_score for v0.3.1 arbitration (0.35-0.75).
"""

import numpy as np
import librosa
import logging

# Segregated Logging: Focused on spectral artifacts and FFT stability
analysis_logger = logging.getLogger("analysis")

def detect_spectral_suspicion(file_path: str, sample_rate: int) -> float:
    """
    Analyzes frequency spectrum for artificial "brickwall" cutoffs.
    Returns a score from 0.0 (Natural) to 1.0 (Highly Suspicious).
    """
    try:
        y, sr = librosa.load(file_path, sr=sample_rate, mono=True)
        if len(y) == 0:
            return 0.0

        # Compute Magnitude Spectrogram (STFT)
        S = np.abs(librosa.stft(y, n_fft=2048))
        
        # Calculate Spectral Rolloff (95% energy threshold)
        rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr, roll_percent=0.95)[0]
        avg_rolloff = np.mean(rolloff)

        nyquist = sr / 2
        
        # v0.3.1 Logic: If rolloff is < 16kHz on high SR files, it's a suspicious transcode
        if avg_rolloff < 16000 and nyquist >= 22050:
            suspicion_score = (16000 - avg_rolloff) / 16000
        else:
            suspicion_score = 0.0

        return float(np.clip(suspicion_score, 0.0, 1.0))

    except Exception as e:
        analysis_logger.error(f"Spectral analysis failure on {file_path}: {str(e)}")
        return 0.5 # Return neutral suspicion on error
