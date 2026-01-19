"""
Audiopro Analysis Pipeline v0.3.1
- Merged Facade: Security + DSP + Metadata.
- Role: Coordinates high-precision extraction into the Data Contract.
"""

import hashlib
from pathlib import Path
from .dsp import calculate_snr, detect_clipping, calculate_suspicion_score
from .metadata import MetadataExtractor
from ..models import AnalysisResult

class AnalysisPipeline:
    def __init__(self, config: dict):
        self.config = config
        self.meta_extractor = MetadataExtractor()

    def _generate_hash(self, file_path: str) -> str:
        """Blake2b hashing for unique file identification."""
        hash_b2 = hashlib.blake2b()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_b2.update(chunk)
        return hash_b2.hexdigest()

    def execute(self, file_path: str) -> AnalysisResult:
        """Runs the full forensic extraction suite."""
        path_obj = Path(file_path)
        
        # 1. DSP Extraction
        snr = calculate_snr(file_path)
        clips = detect_clipping(file_path)
        
        # 2. Suspicion Score (Sentinel Logic)
        weights = self.config["ml_engine"]["sentinel_weights"]
        suspicion = calculate_suspicion_score(snr, clips, weights)
        
        # 3. Metadata Extraction
        metadata = self.meta_extractor.get_info(file_path)
        
        return AnalysisResult(
            file_hash=self._generate_hash(file_path),
            file_name=path_obj.name,
            file_path=str(path_obj.absolute()),
            snr_value=snr,
            clipping_count=clips,
            suspicion_score=suspicion,
            metadata=metadata
        )
