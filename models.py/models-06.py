#"""
# Audiopro v0.3.1
# - Handles deterministic metadata extraction + integrity gates + Random Forest inference wrapper.
# - Role: Brain + Metadata Gate (clean architecture: single canonical hash strategy).
#"""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

try:
    # Mutagen is the most robust lightweight choice for container/codec introspection
    from mutagen import File as MutagenFile  # type: ignore
except Exception:  # pragma: no cover
    MutagenFile = None  # type: ignore


# -----------------------------------------------------------------------------
# Logging (industrial-grade traceability)
# -----------------------------------------------------------------------------

logger_meta = logging.getLogger("audiopro.metadata")
logger_ml = logging.getLogger("audiopro.brain.random_forest")


# -----------------------------------------------------------------------------
# Data contracts (local-only; in canonical project these live in core/models.py)
# -----------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PredictionResult:
    predicted_class: str
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class ModelArtifacts:
    """Loaded model artifacts (immutable for traceability)."""
    model: Any
    scaler_mean: Optional[np.ndarray] = None
    scaler_std: Optional[np.ndarray] = None


# -----------------------------------------------------------------------------
# ML Interface + Random Forest Brain
# -----------------------------------------------------------------------------

class MLModelInterface(ABC):
    """Deterministic classification interface (stable contract)."""

    @abstractmethod
    def load_artifacts(self, artifact_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(self, features: np.ndarray) -> PredictionResult:
        raise NotImplementedError


class RandomForestBrain(MLModelInterface):
    """
    Random Forest Brain wrapper.
    - Loads a pickled sklearn model + optional scaler stats
    - Applies deterministic Z-score normalization
    - Predicts class labels + confidence when predict_proba exists
    """

    def __init__(self) -> None:
        self._artifacts: Optional[ModelArtifacts] = None

    def load_artifacts(self, artifact_path: str) -> None:
        if not os.path.exists(artifact_path):
            logger_ml.error("Artifact not found: %s", artifact_path)
            raise FileNotFoundError(f"Weight file missing: {artifact_path}")

        try:
            with open(artifact_path, "rb") as f:
                data = pickle.load(f)

            if not (isinstance(data, dict) and "model" in data):
                raise ValueError("Unsupported artifact format (expected dict with 'model').")

            model = data["model"]
            mean = data.get("scaler_mean", None)
            std = data.get("scaler_std", None)

            mean_arr = np.array(mean, dtype=np.float64) if mean is not None else None
            std_arr = np.array(std, dtype=np.float64) if std is not None else None

            self._artifacts = ModelArtifacts(model=model, scaler_mean=mean_arr, scaler_std=std_arr)
            logger_ml.info("Artifacts loaded successfully from %s", artifact_path)

        except Exception as e:
            logger_ml.exception("Failed to load artifacts from %s: %s", artifact_path, e)
            raise

    def _normalize(self, x: np.ndarray) -> np.ndarray:
        """Z-score normalization with epsilon guard."""
        if self._artifacts is None:
            return x
        mean = self._artifacts.scaler_mean
        std = self._artifacts.scaler_std
        if mean is None or std is None:
            return x
        return (x - mean) / (std + 1e-9)

    def predict(self, features: np.ndarray) -> PredictionResult:
        if self._artifacts is None or self._artifacts.model is None:
            raise RuntimeError("Model artifacts must be loaded before prediction.")

        x = np.array(features, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        x = self._normalize(x)
        model = self._artifacts.model

        # Prefer predict_proba for confidence reporting
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x)
            idx = int(np.argmax(proba[0]))
            conf = float(proba[0][idx])
            if hasattr(model, "classes_"):
                label = str(model.classes_[idx])
            else:
                label = str(idx)
            return PredictionResult(predicted_class=label, confidence=conf)

        pred = model.predict(x)
        label = str(pred[0]) if isinstance(pred, (list, np.ndarray)) else str(pred)
        return PredictionResult(predicted_class=label, confidence=0.0)

    def predict_proba_if_supported(self, features: np.ndarray) -> Optional[np.ndarray]:
        """Optional: only if the sklearn model provides predict_proba()."""
        if self._artifacts is None or self._artifacts.model is None:
            raise RuntimeError("Model artifacts must be loaded before prediction.")

        model = self._artifacts.model
        if not hasattr(model, "predict_proba"):
            return None

        x = np.array(features, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)
        x = self._normalize(x)
        return model.predict_proba(x)


# -----------------------------------------------------------------------------
# Metadata + Integrity / Anti-spoof Gates (clean architecture: one hash policy)
# -----------------------------------------------------------------------------

class MetadataExpert:
    """
    Metadata + integrity expert.

    Clean architecture decision:
      - Single canonical duplicate detection hash strategy:
        Blake2b 3-point sampling (64KB start + middle + end)
      - No MD5 fast hash (removed to avoid dual policy ambiguity)

    Features:
      - Mutagen-based header inspection (when available)
      - Conservative anti-spoofing (container mismatch + low-bitrate FLAC heuristic)
      - Deterministic, bounded-I/O hashing for duplicate detection
    """

    def __init__(self) -> None:
        self.lossless_extensions = {".FLAC", ".WAV", ".AIFF", ".WV", ".ALAC"}
        self.supported_extensions = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aiff", ".wv", ".alac"}

    def get_forensic_hash_blake2b_3point(self, file_path: str) -> str:
        """
        Blake2b over Start+Middle+End (64KB each) for duplicate detection with bounded I/O.
        """
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"

        try:
            size = os.path.getsize(file_path)
            if size <= 0:
                return "EMPTY_FILE"

            chunk = 64 * 1024
            h = hashlib.blake2b()

            with open(file_path, "rb") as f:
                # Start
                h.update(f.read(chunk))

                # Middle
                if size > 2 * chunk:
                    mid = max((size // 2) - (chunk // 2), 0)
                    f.seek(mid, os.SEEK_SET)
                    h.update(f.read(chunk))

                # End
                if size > chunk:
                    end = max(size - chunk, 0)
                    f.seek(end, os.SEEK_SET)
                    h.update(f.read(chunk))

            return h.hexdigest()

        except Exception as e:
            logger_meta.exception("Forensic hash failure %s: %s", file_path, e)
            return "HASH_ERROR"

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Extract technical specs and run integrity gates.
        Returned dict is suitable for persistence as AnalysisResult.metadata.
        """
        if not os.path.exists(file_path):
            return self._error_state("MISSING")

        ext = os.path.splitext(file_path)[1]
        ext_lower = ext.lower()
        ext_upper = ext.upper()

        if ext_lower and ext_lower not in self.supported_extensions:
            return {**self._error_state("UNSUPPORTED_EXT"), "format_ext": ext_upper}

        try:
            st = os.stat(file_path)
            filesize_mb = round(st.st_size / (1024 * 1024), 2)

            baseline: Dict[str, Any] = {
                "hash_forensic": self.get_forensic_hash_blake2b_3point(file_path),
                "format_ext": ext_upper,
                "format_internal": "UNKNOWN",
                "filesize_mb": filesize_mb,
                "bitrate_kbps": 0,
                "sample_rate": 0,
                "channels": 0,
                "bits_per_sample": None,
                "is_spoofed": False,
                "is_lossless": ext_upper in self.lossless_extensions,
                "status": "PARTIAL",
            }

            if MutagenFile is None:
                baseline["format_internal"] = "UNKNOWN_NO_MUTAGEN"
                baseline["status"] = "VALIDATED_NO_MUTAGEN"
                return baseline

            audio = MutagenFile(file_path, easy=True)
            if not audio or not getattr(audio, "info", None):
                return self._error_state("CORRUPT_HEADER")

            info = audio.info
            fmt_internal = type(audio).__name__.replace("Easy", "").replace("FileType", "")
            baseline["format_internal"] = fmt_internal

            sample_rate = int(getattr(info, "sample_rate", 0) or 0)
            channels = int(getattr(info, "channels", 0) or 0)
            bits = getattr(info, "bits_per_sample", None)
            bitrate = int(getattr(info, "bitrate", 0) or 0)
            bitrate_kbps = bitrate // 1000 if bitrate else 0

            is_spoofed = self._verify_integrity(
                ext_lower=ext_lower,
                fmt_internal_upper=fmt_internal.upper(),
                bitrate=bitrate,
                sample_rate=sample_rate,
                channels=channels,
            )

            baseline.update(
                {
                    "bitrate_kbps": bitrate_kbps,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "bits_per_sample": bits,
                    "is_spoofed": bool(is_spoofed),
                    "is_lossless": bool(ext_upper in self.lossless_extensions and "MP3" not in fmt_internal.upper()),
                    "status": "SPOOF_ALERT" if is_spoofed else "VALIDATED",
                }
            )
            return baseline

        except Exception as e:
            logger_meta.exception("Metadata failure on %s: %s", file_path, e)
            return self._error_state("CRASHED")

    def _verify_integrity(
        self,
        *,
        ext_lower: str,
        fmt_internal_upper: str,
        bitrate: int,
        sample_rate: int,
        channels: int,
    ) -> bool:
        """Deterministic anti-spoofing gate (conservative)."""
        # 1) Container mismatch checks
        if ext_lower == ".flac" and "FLAC" not in fmt_internal_upper:
            return True
        if ext_lower in (".wav", ".aiff", ".aif", ".aiffc") and not any(x in fmt_internal_upper for x in ("WAVE", "AIFF")):
            return False

        # 2) Transcode heuristic: very low bitrate FLAC is suspicious
        if ext_lower == ".flac" and bitrate and bitrate < 128_000:
            return True

        # 3) Plausibility checks
        if sample_rate and (sample_rate < 8_000 or sample_rate > 384_000):
            return True
        if channels and (channels < 1 or channels > 16):
            return True

        return False

    @staticmethod
    def _error_state(reason: str) -> Dict[str, Any]:
        return {
            "hash_forensic": "",
            "format_ext": "ERROR",
            "format_internal": "ERROR",
            "filesize_mb": 0,
            "bitrate_kbps": 0,
            "sample_rate": 0,
            "channels": 0,
            "bits_per_sample": None,
            "is_spoofed": True,
            "is_lossless": False,
            "status": reason,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger_ml.info("Audiopro Brain/Metadata (clean hash policy) module initialized.")

