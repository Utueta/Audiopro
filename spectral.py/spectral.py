#"""
# Audiopro v0.3.1
# - Handles deterministic spectral-domain auditing (rolloff, aliasing risk).
#"""

from __future__ import annotations

import logging

import numpy as np
import librosa

librosa.cache(level=40)

from .dsp_profile import compute_stft_profile_from_sr

analysis_logger = logging.getLogger("analysis")


def _nyquist_aliasing_score(S_power: np.ndarray, sr: int) -> float:
    """Heuristic aliasing indicator: energy concentration near Nyquist."""
    if sr <= 0 or S_power.size == 0:
        return 0.0
    n_freq = S_power.shape[0]
    # top 5% frequency bins vs mid band (20-40%)
    top = int(max(1, n_freq * 0.05))
    mid_lo = int(n_freq * 0.20)
    mid_hi = int(n_freq * 0.40)
    e_top = float(np.mean(S_power[-top:, :]))
    e_mid = float(np.mean(S_power[mid_lo:mid_hi, :])) + 1e-18
    ratio = e_top / e_mid
    # map ratio to [0,1] with saturation
    return float(np.clip((ratio - 0.5) / 2.0, 0.0, 1.0))


def detect_spectral_suspicion(file_path: str, sample_rate: int) -> float:
    """Returns a normalized [0,1] suspicion score from spectral-domain signals.

    Requirements enforced:
      - Spectral roll-off is sample-rate adaptive:
          threshold = 0.95 * (sample_rate / 2)
      - Nyquist aliasing detection contributes to suspicion.
    """
    try:
        y, sr = librosa.load(file_path, sr=sample_rate, mono=True, dtype="float64")
        if y.size == 0:
            return 0.0

        prof = compute_stft_profile_from_sr(int(sr))
        S = librosa.stft(
            y,
            n_fft=prof.n_fft,
            hop_length=prof.hop_length,
            window="hann",
            center=True,
        )
        P = np.abs(S) ** 2

        # Roll-off frequency at 95% energy
        roll = librosa.feature.spectral_rolloff(S=P, sr=sr, roll_percent=0.95)[0]
        avg_roll_hz = float(np.mean(roll))

        nyquist = float(sr) / 2.0
        adaptive_thresh = 0.95 * nyquist

        roll_susp = 1.0 if avg_roll_hz < adaptive_thresh else 0.0

        alias_susp = _nyquist_aliasing_score(P, int(sr))

        # Combine conservatively: roll-off is strong signal; aliasing is corroborative
        score = 0.7 * roll_susp + 0.3 * alias_susp
        return float(np.clip(score, 0.0, 1.0))
    except Exception as e:
        analysis_logger.error(f"Spectral suspicion error: {e}")
        return 0.0
