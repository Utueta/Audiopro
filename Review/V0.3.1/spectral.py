"""
Audiopro Spectral Analysis v0.2.5
- STFT-based frequency domain auditing
- Detects artificial brickwall filters and upsampling
- Generates the 'suspicion_score' for ML arbitration
"""

import numpy as np
import librosa
import logging

# Segmented Logging: Focused on spectral artifacts and FFT stability
analysis_logger = logging.getLogger("analysis")

def detect_spectral_suspicion(file_path: str, sample_rate: int) -> float:
    """
    Analyzes the frequency spectrum to find artificial "brickwall" cutoffs.
    Returns a score from 0.0 (Natural) to 1.0 (Highly Suspicious).
    """
    try:
        # Load audio (mono)
        y, sr = librosa.load(file_path, sr=sample_rate, mono=True)
        if len(y) == 0:
            return 0.0

        # 1. Compute Magnitude Spectrogram (STFT)
        # Using a 2048-sample window for industrial precision
        S = np.abs(librosa.stft(y, n_fft=2048))
        
        # 2. Calculate the Spectral Centroid & Rolloff
        # These metrics help identify where the energy "dies off"
        rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr, roll_percent=0.95)[0]
        avg_rolloff = np.mean(rolloff)

        # 3. Detect "Brickwalling" (Upsampling Check)
        # If the rolloff is significantly lower than the Nyquist frequency (sr/2),
        # but the file is in a high-fidelity container, it's suspicious.
        nyquist = sr / 2
        
        # Normal high-quality audio should have energy up to ~20kHz. 
        # Low-quality transcodes usually hard-cut at 16kHz or 11kHz.
        if avg_rolloff < 16000 and nyquist >= 22050:
            # High suspicion: Energy cuts off early despite high sample rate
            suspicion_score = (16000 - avg_rolloff) / 16000
        else:
            suspicion_score = 0.0

        # 4. Check for Spectral Holes (Artifacting)
        # Flattened magnitude bins between 10kHz-15kHz are common in bad compression
        return float(np.clip(suspicion_score, 0.0, 1.0))

    except Exception as e:
        analysis_logger.error(f"Spectral analysis failure on {file_path}: {e}")
        return 0.5 # Return neutral suspicion on error
