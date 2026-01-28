#"""
# Audiopro v0.3.1
# - Handles deterministic audio ingest: security gates + hashing + DSP + metadata.
#"""

from __future__ import annotations

import hashlib
import os
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import librosa

# Avoid redundant STFT computations across identical calls (deterministic cache).
librosa.cache(level=40)

try:
    import pyloudnorm as pyln  # type: ignore
except Exception:  # pragma: no cover
    pyln = None

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
        """Blake2b hash on 3-point sampling: start + middle + end 64KB (deterministic)."""
        t0 = time.perf_counter()
        size = os.path.getsize(file_path)

        h = hashlib.blake2b(digest_size=16)  # 128-bit identity
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
        """Deterministic stratified sampling segments."""
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
        segmented: bool,
        seed: int,
    ) -> Tuple[List[Tuple[float, float, "librosa.util.np.ndarray", int]], float]:
        """Loads audio as float64, preserving original SR (sr=None)."""
        duration_s = float(librosa.get_duration(path=file_path))
        segments: List[Tuple[float, float, "librosa.util.np.ndarray", int]] = []

        if not segmented:
            y, sr = librosa.load(file_path, sr=None, mono=False, dtype="float64")
            segments.append((0.0, duration_s, y, int(sr)))
            return segments, duration_s

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

    def analyze_file(self, file_path: str, *, is_segmented: Optional[bool] = None) -> AnalysisResult:
        """Runs the full forensic extraction suite."""
        path_obj = Path(file_path)

        file_hash, hash_io = self._blake2b_3point_hash(file_path)
        seed = int(file_hash[:16], 16)

        metadata = self.meta_extractor.get_info(file_path) or {}
        metadata["hash_io"] = hash_io

        # Determine segmented mode: explicit parameter overrides config.
        if is_segmented is None:
            mode = str(self.config.get("analysis", {}).get("loading_mode", "segmented")).lower()
            segmented = mode == "segmented"
        else:
            segmented = bool(is_segmented)

        metadata["loading_mode"] = "segmented" if segmented else "full"

        segments, duration_s = self._load_audio(file_path, segmented=segmented, seed=seed)

        # Compute SR-adaptive STFT profile for traceability
        sr = int(metadata.get("sample_rate") or segments[0][3] or 0)
        if sr > 0:
            metadata["stft_profile"] = asdict(compute_stft_profile_from_sr(sr))

        # Aggregate worst-case metrics across segments
        snr_db_min = float("inf")
        true_peak_max = 0.0
        clipping_events_max = 0
        crackle_density_max = 0.0
        ms_ratio_min = float("inf")
        iacc_val = None

        for (_, _, y, seg_sr) in segments:
            snr_db = calculate_snr_db(y, seg_sr)
            snr_db_min = min(snr_db_min, snr_db)

            tp, clip_events = detect_true_peak_clipping(y, seg_sr)
            true_peak_max = max(true_peak_max, tp)
            clipping_events_max = max(clipping_events_max, clip_events)

            cd = crackling_density(y, seg_sr)
            crackle_density_max = max(crackle_density_max, cd)

            ms_ratio, _ = stereo_integrity_metrics(y, seg_sr, compute_iacc=False)
            ms_ratio_min = min(ms_ratio_min, ms_ratio)

        if snr_db_min == float("inf"):
            snr_db_min = 0.0

        # Suspicion score (deterministic heuristic)
        weights = self.config.get("ml_engine", {}).get("sentinel_weights", {})
        suspicion = float(calculate_suspicion_score(snr_db_min, clipping_events_max, weights))

        # IACC corroboration only in gray zone
        if 0.4 < suspicion < 0.7 and segments:
            ms_ratio, iacc = stereo_integrity_metrics(segments[0][2], segments[0][3], compute_iacc=True)
            ms_ratio_min = min(ms_ratio_min, ms_ratio)
            iacc_val = iacc

        # Loudness normalization detection (best-effort)
        if pyln is not None and segments and segments[0][3] > 0:
            try:
                y0 = segments[0][2]
                sr0 = segments[0][3]
                y_mono = y0 if getattr(y0, "ndim", 1) == 1 else (y0[0] * 0.5 + y0[1] * 0.5)
                meter = pyln.Meter(int(sr0))
                lufs = float(meter.integrated_loudness(y_mono))
                metadata["lufs_integrated"] = lufs
                # Heuristic: unusually tight normalization around broadcast targets
                metadata["loudness_normalization_suspect"] = bool(-16.5 <= lufs <= -13.5)
            except Exception:
                pass

        metadata["duration_s"] = float(duration_s)
        metadata["true_peak_max"] = float(true_peak_max)
        metadata["crackling_density_max"] = float(crackle_density_max)
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
            was_segmented=bool(segmented),
        )
