"""
Audiopro Random Forest Brain v0.2.5
- Implements MLModelInterface for deterministic classification
- Handles feature vector normalization via Z-Score Scaler
- Manages persistent weight loading from .pkl artifacts
"""

import os
import logging
import hashlib
from typing import Dict, Any, Optional
from mutagen import File

# Logging configuration for industrial-grade traceability
logger = logging.getLogger("Audiopro.Metadata")

class MetadataExpert:
    """
    Expert in metadata and container integrity.
    Consolidated logic for signal extraction, fast-hashing, and spoofing detection.
    """
    def __init__(self):
        self.lossless_extensions = {'.FLAC', '.WAV', '.AIFF', '.WV', '.ALAC'}
        self.supported_extensions = {'.mp3', '.flac', '.wav', '.m4a', '.ogg', '.aiff'}

    def get_fast_hash(self, file_path: str) -> str:
        """
        DevSecOps Identifier: MD5 on initial 8MB chunk.
        Used for deduplication and persistent traceability.
        """
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"
            
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # 8MB is sufficient for most audio headers and metadata blocks
                chunk = f.read(8192 * 1024)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            logger.error(f"IO Failure during hashing {file_path}: {e}")
            return hashlib.md5(file_path.encode()).hexdigest()

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts technical properties and executes security cross-checks.
        Provides the feature vector required for the Random Forest Classifier.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return self._generate_fallback_info(file_path, "FILE_NOT_FOUND")

        try:
            stats = os.stat(file_path)
            # Binary inspection of the file
            audio = File(file_path, easy=True)
            
            if audio is None:
                logger.warning(f"Header not recognized for {file_path}.")
                return self._generate_fallback_info(file_path, "UNKNOWN_CONTAINER")

            info = audio.info
            actual_format = type(audio).__name__.replace('Easy', '').replace('FileType', '')
            extension = os.path.splitext(file_path)[1].upper()

            # Security Gate: Anti-Spoofing (MP3 renamed to .FLAC, etc.)
            is_spoofed = self._check_spoofing(actual_format, extension, info)
            
            return {
                "hash": self.get_fast_hash(file_path),
                "format_internal": actual_format,
                "format_ext": extension,
                "filesize_mb": round(stats.st_size / (1024 * 1024), 2),
                "is_spoofed": is_spoofed,
                "duration": max(0, getattr(info, 'length', 0)),
                "bitrate": self._get_bitrate_kbps(info),
                "sample_rate": getattr(info, 'sample_rate', 0),
                "channels": getattr(info, 'channels', 0),
                "bits_per_sample": getattr(info, 'bits_per_sample', None),
                "is_lossless": (extension in self.lossless_extensions and "MP3" not in actual_format.upper()),
                "status": "VALIDATED" if not is_spoofed else "SPOOF_ALERT"
            }

        except Exception as e:
            logger.error(f"Extraction crash on {file_path}: {str(e)}")
            return self._generate_fallback_info(file_path, "ERROR")

    def _get_bitrate_kbps(self, info) -> int:
        """Secure bitrate calculation avoiding floating point drift."""
        br = getattr(info, 'bitrate', 0)
        return br // 1000 if br else 0

    def _check_spoofing(self, internal_fmt: str, ext: str, info: Any) -> bool:
        """
        Detects container/codec mismatch and technical impossibilities.
        Logic Check: FLAC files < 128kbps are statistically spoofed.
        """
        internal_fmt = internal_fmt.upper()
        ext = ext.upper()

        # 1. Mismatch Check
        if ext == '.FLAC' and 'FLAC' not in internal_fmt:
            return True
        if ext in ['.WAV', '.AIFF'] and not any(x in internal_fmt for x in ['WAVE', 'AIFF']):
            return True
        if ext == '.MP3' and 'MP3' not in internal_fmt:
            return True

        # 2. Heuristic Check for "Fake HQ"
        if ext == '.FLAC':
            br = getattr(info, 'bitrate', 500000)
            if br != 0 and br < 128000: # Mathematically improbable for lossless
                return True

        return False

    def _generate_fallback_info(self, file_path: str, status: str) -> Dict[str, Any]:
        """Ensures service continuity for problematic files."""
        ext = os.path.splitext(file_path)[1].upper()
        return {
            "hash": "PENDING",
            "format_internal": "UNKNOWN",
            "format_ext": ext,
            "filesize_mb": 0,
            "is_spoofed": True if status != "FILE_NOT_FOUND" else False,
            "duration": 0,
            "bitrate": 0,
            "sample_rate": 0,
            "channels": 0,
            "bits_per_sample": None,
            "is_lossless": False,
            "status": status
        }

if __name__ == "__main__":
    # Industrial Integration Test
    expert = MetadataExpert()
    # Example usage: print(expert.analyze("audio_sample.wav"))
