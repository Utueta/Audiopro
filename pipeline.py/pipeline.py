#"""
# Audiopro v0.3.1
# - Handles deterministic audio ingest: security gates + hashing + DSP + metadata.
#"""

from __future__ import annotations

import hashlib
import os
import time
import random
from dataclasses import asdict

try:
    import pyloudnorm as pyln  # type: ignore
except Exception:  # pragma: no cover
    pyln = None

from pathlib import Path
from typing import Dict, List, Tuple

import librosa

# Reduce redundant STFT computations across identical calls (deterministic cache).
librosa.cache(level=40)

from .dsp import (
    calculate_snr_db,
    detect_true_peak_clipping,
    calculate_suspicion_score,
    crackling_density,
    stereo_integrity_metrics,
)
from .metadata import MetadataExtractor
from .dsp_profile import compute_stft_profile_from_sr
from ..models import AnalysisResult


_HASH_SAMPLE_BYTES = 64 * 1024  # 64KB


class AudioAnalysisPipeline:
    """Deterministic analysis facade (ingest → hashing → DSP/features → contract)."""

    def __init__(self, config: dict):
        self.config = config
        self.meta_extractor = MetadataExtractor()

    def _blake2b_3point_hash(self, file_path: str) -> Tuple[str, Dict[str, float]]:
        """Blake2b hash on 3-point sampling: start + middle + end 64KB (deterministic).

        Returns (hex_digest, io_telemetry).
        """
        t0 = time.perf_counter()
        size = os.path.getsize(file_path)

        h = hashlib.blake2b(digest_size=16)  # 128-bit identity as per spec

        read_total = 0

        with open(file_path, "rb") as f:
            # start
            start = f.read(_HASH_SAMPLE_BYTES)
            h.update(start)
            read_total += len(start)

            # middle
            if size > _HASH_SAMPLE_BYTES:
                mid_off = max(0, (size // 2) - (_HASH_SAMPLE_BYTES // 2))
                f.seek(mid_off, os.SEEK_SET)
                mid = f.read(_HASH_SAMPLE_BYTES)
                h.update(mid)
                read_total += len(mid)

            # end
            if size > _HASH_SAMPLE_BYTES:
                end_off = max(0, size - _HASH_SAMPLE_BYTES)
                f.seek(end_off, os.SEEK_SET)
                end = f.read(_HASH_SAMPLE_BYTES)
                h.update(end)
                read_total += len(end)

        dt = time.perf_counter() - t0
        io = {
            "hash_bytes_read": float(read_total),
            "hash_read_seconds": float(dt),
            "hash_read_mbps": float((read_total / (1024 * 1024)) / dt) if dt > 0 else 0.0,
        }
        return h.hexdigest(), io

    def _select_segments(self, duration_s: float, seed: int) -> List[Tuple[float, float]]:
        """Deterministic segmented loading strategy.

        Segments:
          - First 30s
          - Middle 10s
          - Last 10s
          - Random 5s (deterministic via seed)
        """
        if duration_s <= 0:
            return [(0.0, 0.0)]

        segs: List[Tuple[float, float]] = []

        # First 30s
        segs.append((0.0, min(30.0, duration_s)))

        # Middle 10s
        if duration_s > 10.0:
            mid_start = max(0.0, (duration_s / 2.0) - 5.0)
            segs.append((mid_start, min(10.0, duration_s - mid_start)))

        # Last 10s
        if duration_s > 10.0:
            last_start = max(0.0, duration_s - 10.0)
            segs.append((last_start, min(10.0, duration_s - last_start)))

        # Random 5s (deterministic)
        if duration_s > 5.0:
            rng = random.Random(seed)
            start = rng.uniform(0.0, max(0.0, duration_s - 5.0))
            segs.append((start, 5.0))

        # De-duplicate near-identical segments
        dedup: List[Tuple[float, float]] = []
        for s in segs:
            if all(abs(s[0] - d[0]) > 0.25 for d in dedup):
                dedup.append(s)
        return dedup

    def _load_audio(
        self,
        file_path: str,
        *,
        mode: str,
        seed: int,
    ) -> Tuple[List[Tuple[float, float, "librosa.util.np.ndarray", int]], float]:
        """Loads audio as float64, preserving SR (sr=None)."""
        duration_s = float(librosa.get_duration(path=file_path))
        segments: List[Tuple[float, float, "librosa.util.np.ndarray", int]] = []

        if mode == "full":
            y, sr = librosa.load(file_path, sr=None, mono=False, dtype="float64")
            segments.append((0.0, duration_s, y, int(sr)))
            return segments, duration_s

        # segmented
        for (off, dur) in self._select_segments(duration_s, seed):
            y, sr = librosa.load(
                file_path,
                sr=None,
                mono=False,
                offset=float(off),
                duration=float(dur) if dur > 0 else None,
                dtype="float64",
            )
            segments.append((off, dur, y, int(sr)))
        return segments, duration_s

    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Runs the full forensic extraction suite."""
        path_obj = Path(file_path)

        file_hash, hash_io = self._blake2b_3point_hash(file_path)
        seed = int(file_hash[:16], 16)  # deterministic segment selection seed

        # Metadata extraction (container-level)
        metadata = self.meta_extractor.get_info(file_path) or {}
        metadata["hash_io"] = hash_io

        # Loading strategy
        mode = str(self.config.get("analysis", {}).get("loading_mode", "segmented")).lower()
        if mode not in ("segmented", "full"):
            mode = "segmented"
        metadata["loading_mode"] = mode

        segments, duration_s = self._load_audio(file_path, mode=mode, seed=seed)

        # Compute SR-adaptive STFT profile (traceability)
        # Prefer header SR if available; fall back to first loaded segment SR.
        sr = int(metadata.get("sample_rate") or segments[0][3] or 0)
        if sr > 0:
            stft_profile = compute_stft_profile_from_sr(sr)
            metadata["stft_profile"] = asdict(stft_profile)

        # DSP extraction aggregated across segments (worst-case for defects)
        snr_db_min = float("inf")
        true_peak_max = 0.0
        clipping_events_max = 0
        crackle_density_max = 0.0
        ms_ratio_min = float("inf")
        iacc_val = None

        for (off, dur, y, seg_sr) in segments:
            # SNR (dB), epsilon-guarded
            snr_db = calculate_snr_db(y, seg_sr)
            snr_db_min = min(snr_db_min, snr_db)

            # True Peak clipping (ITU-R BS.1770-style oversampling)
            tp, clip_events = detect_true_peak_clipping(y, seg_sr)
            true_peak_max = max(true_peak_max, tp)
            clipping_events_max = max(clipping_events_max, clip_events)

            # Crackling density (Audacity-style click detection proxy)
            cd = crackling_density(y, seg_sr)
            crackle_density_max = max(crackle_density_max, cd)

            # Stereo integrity metrics (M/S ratio primary; IACC only if doubtful later)
            ms_ratio, iacc = stereo_integrity_metrics(y, seg_sr, compute_iacc=False)
            ms_ratio_min = min(ms_ratio_min, ms_ratio)
            # store IACC only once if computed
            if iacc is not None:
                iacc_val = iacc

        if snr_db_min == float("inf"):
            snr_db_min = 0.0

        # Suspicion score (deterministic weighted heuristic)
        weights = self.config.get("ml_engine", {}).get("sentinel_weights", {})
        suspicion = float(calculate_suspicion_score(snr_db_min, clipping_events_max, weights))

        # Corroborate pseudo-stereo only if in gray zone (doubtful)
        if 0.4 < suspicion < 0.7:
            ms_ratio, iacc = stereo_integrity_metrics(segments[0][2], segments[0][3], compute_iacc=True)
            ms_ratio_min = min(ms_ratio_min, ms_ratio)
            iacc_val = iacc

        metadata["duration_s"] = float(duration_s)
        metadata["true_peak_max"] = float(true_peak_max)
        metadata["crackling_density_max"] = float(crackle_density_max)

        # Loudness normalization detection (EBU R128 / ReplayGain proxy) via pyloudnorm
        if pyln is not None and segments and segments[0][3] > 0:
            try:
                y0 = segments[0][2]
                sr0 = segments[0][3]
                # pyloudnorm expects mono float
                y_mono = y0 if getattr(y0, "ndim", 1) == 1 else (y0[0] * 0.5 + y0[1] * 0.5)
                meter = pyln.Meter(sr0)
                lufs = float(meter.integrated_loudness(y_mono))
                metadata["lufs_integrated"] = lufs
                # Common targets: -23 LUFS (EBU), -14 LUFS (streaming). Flag if extremely close.
                metadata["loudness_normalization_suspect"] = bool(min(abs(lufs + 23.0), abs(lufs + 14.0)) < 0.8)
            except Exception:
                pass

        metadata["ms_energy_ratio_min"] = float(ms_ratio_min if ms_ratio_min != float("inf") else 0.0)
        if iacc_val is not None:
            metadata["iacc"] = float(iacc_val)

        return AnalysisResult(
            file_hash=file_hash,
            file_name=path_obj.name,
            file_path=str(path_obj.absolute()),
            snr_value=float(snr_db_min),
            clipping_count=int(clipping_events_max),
            suspicion_score=float(suspicion),
            metadata=metadata,
        )
