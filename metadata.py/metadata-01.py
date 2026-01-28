#"""
# Audiopro v0.3.1
# - Handles metadata integrity auditing + deterministic Random Forest inference with persistent scaler artifacts.
# - Role: "Brain + Metadata Gate" consolidated script (portable, pasteable, production-aware).
#"""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    from mutagen import File as MutagenFile  # type: ignore
except Exception:  # pragma: no cover
    MutagenFile = None


# -----------------------------------------------------------------------------
# Logging (industrial-grade traceability)
# -----------------------------------------------------------------------------

logger_meta = logging.getLogger("Audiopro.Metadata")
logger_ml = logging.getLogger("Audiopro.RandomForest")


# -----------------------------------------------------------------------------
# Data contracts (local-only; in the full project these live in core/models.py)
# -----------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PredictionResult:
    predicted_class: str
    confidence: float = 0.0


# -----------------------------------------------------------------------------
# Metadata Gate (best-of: structural audit + spoofing detection + fast hash)
# -----------------------------------------------------------------------------

class MetadataExpert:
    """Structural file auditor and integrity gate.

    Responsibilities:
      - File existence and extension sanity
      - Header inspection (via mutagen when available)
      - Container/codec mismatch detection
      - Fast hash for dedupe pre-check (MD5 on initial 8MB chunk, deterministic)

    Notes:
      - In the full v0.3.1 spec, canonical duplicate hashing uses Blake2b 3-point sampling.
        This class keeps the legacy 'fast hash' as an optional pre-check only.
    """

    def __init__(self) -> None:
        self.lossless_extensions = {".FLAC", ".WAV", ".AIFF", ".WV", ".ALAC"}
        self.supported_extensions = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aiff", ".aif", ".aiffc"}

    def get_fast_hash_md5_8mb(self, file_path: str) -> str:
        """MD5 over initial 8MB (DevSecOps fast identifier; deterministic).

        This is NOT a cryptographic identity for forensic dedupe. Use Blake2b 3-point sampling for that.
        """
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"

        h = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8 * 1024 * 1024)  # 8MB
                h.update(chunk)
            return h.hexdigest()
        except (OSError, IOError) as e:
            logger_meta.error("IO failure during hashing %s: %s", file_path, e)
            # deterministic fallback (not content-based; used only to preserve continuity)
            return hashlib.md5(file_path.encode("utf-8", errors="ignore")).hexdigest()

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """Extracts technical specs and executes integrity cross-checks."""
        if not os.path.exists(file_path):
            return self._error_state("MISSING")

        ext_upper = os.path.splitext(file_path)[1].upper()
        ext_lower = os.path.splitext(file_path)[1].lower()

        if ext_lower and ext_lower not in {e.lower() for e in self.supported_extensions}:
            # Not necessarily invalid, but unsupported for strict operation
            return self._error_state("UNSUPPORTED_EXTENSION")

        stats = os.stat(file_path)
        out: Dict[str, Any] = {
            "fast_hash_md5_8mb": self.get_fast_hash_md5_8mb(file_path),
            "format_ext": ext_upper,
            "filesize_mb": round(stats.st_size / (1024 * 1024), 2),
            "bitrate_kbps": 0,
            "sample_rate": 0,
            "channels": 0,
            "bits_per_sample": None,
            "format_internal": "UNKNOWN",
            "is_lossless": bool(ext_upper in self.lossless_extensions),
            "is_spoofed": False,
            "status": "PARTIAL",
        }

        if MutagenFile is None:
            # Header inspection not available; return partial metadata deterministically
            out["status"] = "NO_MUTAGEN"
            return out

        try:
            audio = MutagenFile(file_path, easy=True)
            if not audio or not getattr(audio, "info", None):
                return self._error_state("CORRUPT_HEADER")

            info = audio.info
            internal_fmt = type(audio).__name__.replace("Easy", "").replace("FileType", "")
            out["format_internal"] = internal_fmt

            out["bitrate_kbps"] = self._bitrate_kbps(info)
            out["sample_rate"] = int(getattr(info, "sample_rate", 0) or 0)
            out["channels"] = int(getattr(info, "channels", 0) or 0)
            out["bits_per_sample"] = getattr(info, "bits_per_sample", None)

            is_spoofed = self._verify_integrity(file_path, audio, info)
            out["is_spoofed"] = bool(is_spoofed)
            out["is_lossless"] = bool(
                (ext_upper in self.lossless_extensions) and ("MP3" not in internal_fmt.upper())
            )
            out["status"] = "VALIDATED" if not is_spoofed else "SPOOF_ALERT"
            return out

        except Exception as e:
            logger_meta.error("Metadata failure on %s: %s", file_path, e)
            return self._error_state("CRASHED")

    def _bitrate_kbps(self, info: Any) -> int:
        br = int(getattr(info, "bitrate", 0) or 0)
        return br // 1000 if br > 0 else 0

    def _verify_integrity(self, path: str, audio_obj: Any, info: Any) -> bool:
        """Deterministic anti-spoofing heuristics."""
        ext = os.path.splitext(path)[1].lower()
        internal_fmt = type(audio_obj).__name__.upper()

        # 1) Container mismatch checks
        if ext == ".flac" and "FLAC" not in internal_fmt:
            return True

        if ext in (".wav", ".aiff", ".aif", ".aiffc"):
            # Conservative: accept some non-standard headers (avoid false positives)
            if not any(x in internal_fmt for x in ("WAVE", "AIFF")):
                return False

        # 2) Transcode heuristic: implausibly low bitrate for FLAC
        if ext == ".flac":
            br = int(getattr(info, "bitrate", 500000) or 0)
            if br != 0 and br < 128000:
                return True

        return False

    def _error_state(self, reason: str) -> Dict[str, Any]:
        return {
            "fast_hash_md5_8mb": "",
            "format_ext": "ERROR",
            "format_internal": "ERROR",
            "filesize_mb": 0.0,
            "bitrate_kbps": 0,
            "sample_rate": 0,
            "channels": 0,
            "bits_per_sample": None,
            "is_lossless": False,
            "is_spoofed": True,
            "status": reason,
        }


# -----------------------------------------------------------------------------
# ML Interface + Random Forest Brain (best-of: deterministic, persistent scaler)
# -----------------------------------------------------------------------------

class MLModelInterface(ABC):
    """Deterministic classification interface for long-lived compatibility."""

    @abstractmethod
    def load_artifacts(self, artifact_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(self, features: np.ndarray) -> PredictionResult:
        raise NotImplementedError


class RandomForestBrain(MLModelInterface):
    """Random Forest 'Sentinel Brain' with persistent scaler parameters.

    Artifact format (pickle dict) should include:
      - "model": a sklearn-like estimator implementing predict_proba or predict
      - "scaler_mean": array-like or None
      - "scaler_std": array-like or None

    Determinism considerations:
      - Prediction is deterministic given fixed artifacts and fixed float inputs.
      - Normalization uses stable epsilon guard (1e-9) to avoid division by zero.
    """

    def __init__(self) -> None:
        self.model: Any = None
        self.scaler_mean: Optional[np.ndarray] = None
        self.scaler_std: Optional[np.ndarray] = None

    def load_artifacts(self, artifact_path: str) -> None:
        if not os.path.exists(artifact_path):
            logger_ml.error("Artifact not found at %s", artifact_path)
            raise FileNotFoundError(f"Weight file missing: {artifact_path}")

        try:
            with open(artifact_path, "rb") as f:
                data = pickle.load(f)

            if "model" not in data:
                raise ValueError("Artifact missing required key: 'model'")

            self.model = data["model"]

            mean = data.get("scaler_mean", None)
            std = data.get("scaler_std", None)

            self.scaler_mean = np.array(mean, dtype=np.float64) if mean is not None else None
            self.scaler_std = np.array(std, dtype=np.float64) if std is not None else None

            logger_ml.info("Artifacts loaded successfully from %s", artifact_path)

        except Exception as e:
            logger_ml.error("Failed to load artifacts: %s", e)
            raise

    def _normalize(self, x: np.ndarray) -> np.ndarray:
        if self.scaler_mean is None or self.scaler_std is None:
            return x
        return (x - self.scaler_mean) / (self.scaler_std + 1e-9)

    def predict(self, features: np.ndarray) -> PredictionResult:
        if self.model is None:
            raise RuntimeError("Artifacts must be loaded before prediction.")

        x = np.array(features, dtype=np.float64)
        if x.ndim == 1:
            x = x.reshape(1, -1)

        x = self._normalize(x)

        # Prefer predict_proba when available for stable confidence reporting
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(x)
            # pick argmax per row
            idx = int(np.argmax(proba[0]))
            conf = float(proba[0][idx])
            # map to class label if available
            if hasattr(self.model, "classes_"):
                label = str(self.model.classes_[idx])
            else:
                label = str(idx)
            return PredictionResult(predicted_class=label, confidence=conf)

        # fallback: predict only (confidence unknown)
        pred = self.model.predict(x)
        label = str(pred[0]) if isinstance(pred, (list, np.ndarray)) else str(pred)
        return PredictionResult(predicted_class=label, confidence=0.0)


# -----------------------------------------------------------------------------
# Example usage (manual test)
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    meta = MetadataExpert()
    # print(meta.analyze("test_sample.flac"))

    brain = RandomForestBrain()
    # brain.load_artifacts("weights/random_forest.pkl")
    # print(brain.predict(np.array([0.1, 0.2, 0.3])))
    print("Audiopro consolidated MetadataExpert + RandomForestBrain initialized.")

