#"""
# Audiopro v0.3.1
# - Handles deterministic time-domain DSP feature extraction (float64).
#"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

analysis_logger = logging.getLogger("analysis")


def _to_mono(y: np.ndarray) -> np.ndarray:
    if y.ndim == 1:
        return y
    # librosa returns shape (n_channels, n_samples) for mono=False
    if y.ndim == 2:
        return np.mean(y, axis=0)
    return np.asarray(y).reshape(-1)


def calculate_snr_db(y: np.ndarray, sr: int) -> float:
    """Estimates SNR in dB using block RMS noise-floor percentile.

    Numerical stability guard (required):
      20 * log10(max(rms, 1e-10))
    """
    try:
        mono = _to_mono(np.asarray(y, dtype=np.float64))
        if mono.size == 0:
            return 0.0

        # Frame into 100ms blocks for noise floor estimation
        block = max(1, int(sr * 0.1))
        n_blocks = max(1, mono.size // block)
        mono = mono[: n_blocks * block]
        blocks = mono.reshape(n_blocks, block)

        rms = np.sqrt(np.mean(blocks ** 2, axis=1))
        # guard for numerical stability
        rms = np.maximum(rms, 1e-10)

        # Noise floor proxy = 10th percentile RMS
        noise = np.percentile(rms, 10)
        signal = np.percentile(rms, 90)

        # SNR = 20log10(signal/noise) with guards
        snr = 20.0 * np.log10(max(float(signal), 1e-10) / max(float(noise), 1e-10))
        return float(np.clip(snr, -10.0, 80.0))
    except Exception as e:
        analysis_logger.error(f"SNR Error: {e}")
        return 0.0


def detect_true_peak_clipping(y: np.ndarray, sr: int, *, threshold: float = 0.98) -> Tuple[float, int]:
    """True-peak style clipping detection (ITU-R BS.1770-inspired).

    Returns (true_peak_max, clipping_event_count).
    """
    try:
        mono = _to_mono(np.asarray(y, dtype=np.float64))
        if mono.size == 0:
            return 0.0, 0

        # 4x oversample using polyphase resampling if available; fallback to sample peak.
        try:
            from scipy.signal import resample_poly  # type: ignore
            oversampled = resample_poly(mono, up=4, down=1)
            peak = float(np.max(np.abs(oversampled))) if oversampled.size else float(np.max(np.abs(mono)))
            # count threshold crossings (events, not samples)
            mask = np.abs(oversampled) >= threshold
        except Exception:
            peak = float(np.max(np.abs(mono)))
            mask = np.abs(mono) >= threshold

        if mask.size == 0:
            return peak, 0

        # Event count: number of rising edges into clipped region
        clipped = mask.astype(np.int8)
        edges = np.diff(np.concatenate([[0], clipped]))
        events = int(np.sum(edges == 1))
        return float(peak), int(events)
    except Exception as e:
        analysis_logger.error(f"True Peak Clipping Error: {e}")
        return 0.0, 0


def crackling_density(y: np.ndarray, sr: int) -> float:
    """Crackling/click density using Audacity-style click detection proxy.

    Uses:
      - second-order derivative outliers
      - zero-crossing spikes (corroboration)
    Returns events per second.
    """
    try:
        mono = _to_mono(np.asarray(y, dtype=np.float64))
        if mono.size < 8 or sr <= 0:
            return 0.0

        dur = mono.size / float(sr)

        # Second derivative (discontinuity proxy)
        d2 = np.diff(mono, n=2)
        a = np.abs(d2)

        med = np.median(a)
        mad = np.median(np.abs(a - med)) + 1e-12
        thresh = med + 8.0 * mad

        click_mask = a > thresh

        # Convert to event count (rising edges)
        c = click_mask.astype(np.int8)
        edges = np.diff(np.concatenate([[0], c]))
        events = int(np.sum(edges == 1))

        # ZCR spike corroboration (optional damping of false positives)
        # If ZCR is extremely high, boost confidence; else keep as-is.
        zc = np.mean(mono[:-1] * mono[1:] < 0.0)
        if zc < 0.01:
            # very low ZCR, likely tonal; reduce false positives slightly
            events = int(events * 0.8)

        return float(events / max(dur, 1e-6))
    except Exception as e:
        analysis_logger.error(f"Crackling Detection Error: {e}")
        return 0.0


def stereo_integrity_metrics(y: np.ndarray, sr: int, *, compute_iacc: bool) -> Tuple[float, float | None]:
    """Stereo integrity: Mid/Side energy ratio (primary), IACC (corroboration).

    Returns (ms_energy_ratio, iacc_or_None).
    """
    arr = np.asarray(y, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] < 2:
        # Not stereo
        return 0.0, None

    L = arr[0]
    R = arr[1]
    if L.size == 0 or R.size == 0:
        return 0.0, None

    M = 0.5 * (L + R)
    S = 0.5 * (L - R)
    Em = float(np.mean(M * M)) + 1e-18
    Es = float(np.mean(S * S)) + 1e-18
    ms_ratio = float(Es / Em)  # lower implies pseudo-stereo/mono-like

    if not compute_iacc:
        return ms_ratio, None

    # IACC over short-lag window (+/- 1ms) as corroboration
    max_lag = max(1, int(sr * 0.001))
    Lc = L - np.mean(L)
    Rc = R - np.mean(R)
    denom = (np.sqrt(np.sum(Lc * Lc)) * np.sqrt(np.sum(Rc * Rc))) + 1e-18

    best = 0.0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            a = Lc[-lag:]
            b = Rc[: a.size]
        elif lag > 0:
            a = Lc[:-lag]
            b = Rc[lag:]
        else:
            a = Lc
            b = Rc
        if a.size == 0:
            continue
        corr = float(np.sum(a * b) / denom)
        if abs(corr) > abs(best):
            best = corr

    return ms_ratio, float(best)


def calculate_suspicion_score(snr_db: float, clipping_events: int, weights: dict) -> float:
    """Aggregates deterministic DSP metrics into a normalized [0, 1] suspicion score."""
    w_snr = float(weights.get("snr", 0.6))
    w_clip = float(weights.get("clipping", 0.4))

    # Normalize SNR (higher SNR => lower suspicion). Map 0..60 dB => 1..0
    snr_norm = 1.0 - (np.clip(float(snr_db), 0.0, 60.0) / 60.0)

    # Normalize clipping events. Saturate at 50 events for suspicion 1.0
    clip_norm = np.clip(float(clipping_events) / 50.0, 0.0, 1.0)

    score = (w_snr * snr_norm) + (w_clip * clip_norm)
    return float(np.clip(score, 0.0, 1.0))
