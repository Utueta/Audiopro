#"""
# Audiopro v0.3.1
# - Handles deterministic, sample-rate adaptive STFT profile selection.
#"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

WindowType = Literal["hann_periodic"]

@dataclass(frozen=True, slots=True)
class StftProfile:
    """Deterministic STFT profile derived from source sample rate."""
    source_sample_rate_hz: int
    window_type: WindowType
    n_fft: int
    hop_length: int

    dtype: Literal["float64"]
    normalize_waveform_fullscale: bool
    spectrum_representation: Literal["power"]          # P = |X|^2
    normalize_by_window_power: bool                   # P_norm = P / sum(w^2)
    db_eps: float                                     # for 10*log10(P_norm + eps)


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def compute_stft_profile_from_sr(
    source_sample_rate_hz: int,
    *,
    win_sec: float = 0.0426667,   # ~2048 @ 48 kHz baseline (≈42.7 ms)
    n_fft_min: int = 1024,
    n_fft_max: int = 8192,
    overlap_ratio: float = 0.75,  # hop = n_fft * (1 - overlap_ratio)
    db_eps: float = 1e-12,
) -> StftProfile:
    """Pure deterministic function: derive STFT settings from source sample rate."""
    if not isinstance(source_sample_rate_hz, int):
        raise TypeError("source_sample_rate_hz must be an int.")
    if source_sample_rate_hz <= 0:
        raise ValueError("source_sample_rate_hz must be > 0.")
    if win_sec <= 0:
        raise ValueError("win_sec must be > 0.")
    if n_fft_min <= 0 or n_fft_max <= 0 or n_fft_min > n_fft_max:
        raise ValueError("Invalid n_fft_min/n_fft_max bounds.")
    if not (0.0 < overlap_ratio < 1.0):
        raise ValueError("overlap_ratio must be between 0 and 1 (exclusive).")
    if db_eps <= 0.0:
        raise ValueError("db_eps must be > 0.")

    raw = int(round(source_sample_rate_hz * win_sec))
    n_fft = _next_power_of_two(max(1, raw))
    n_fft = max(n_fft_min, min(n_fft, n_fft_max))

    hop = int(round(n_fft * (1.0 - overlap_ratio)))
    hop = max(1, hop)

    return StftProfile(
        source_sample_rate_hz=source_sample_rate_hz,
        window_type="hann_periodic",
        n_fft=n_fft,
        hop_length=hop,
        dtype="float64",
        normalize_waveform_fullscale=True,
        spectrum_representation="power",
        normalize_by_window_power=True,
        db_eps=db_eps,
    )
