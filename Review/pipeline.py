"""
Audiopro Signal Pipeline v0.3.1
- REGRESSION FIX: Re-instated chunked MD5 hashing and Magic Byte security.
- Role: Primary Feature Engineering and Integrity Verification.
"""

import hashlib
import magic
import numpy as np
import librosa
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("system.pipeline")

class AudioPipeline:
    def __init__(self, sample_rate: int = 22050):
        self.sr = sample_rate
        self.mime_detector = magic.Magic(mime=True)

    def _generate_hash(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def verify_and_extract(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            # 1. Security Gate
            mime_type = self.mime_detector.from_file(file_path)
            if not mime_type.startswith("audio/") and mime_type != "application/ogg":
                return None

            # 2. Features & Hash
            file_hash = self._generate_hash(file_path)
            y, _ = librosa.load(file_path, sr=self.sr)
            
            # Metric Calculation
            rms = np.sqrt(np.mean(y**2))
            stft = np.abs(librosa.stft(y))
            noise_floor = np.percentile(stft, 10)
            snr = 20 * np.log10(rms / noise_floor) if noise_floor > 0 else 100.0
            clipping = int(np.sum(np.abs(y) >= 0.99))

            return {
                "hash": file_hash,
                "mime": mime_type,
                "snr": float(np.clip(snr, -10, 100)),
                "clipping": clipping,
                "raw_audio": y
            }
        except Exception as e:
            logger.error(f"Pipeline failure: {e}")
            return None
