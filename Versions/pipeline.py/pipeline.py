"""
Facade pattern for DSP subsystem.
Single entry point hiding internal analyzer complexity.
"""
from pathlib import Path
from typing import Tuple
import logging

from .dsp import DSPAnalyzer
from .spectral import SpectralAnalyzer
from .metadata import MetadataExtractor
from ..models import AudioMetadata, DSPAnalysis, SpectralAnalysis


logger = logging.getLogger(__name__)


class AudioAnalysisPipeline:
    """
    Coordinates all DSP analyzers and returns unified result.
    Manager.py only needs to call pipeline.analyze(), not individual analyzers.
    """
    
    def __init__(self):
        self._dsp = DSPAnalyzer()
        self._spectral = SpectralAnalyzer()
        self._metadata = MetadataExtractor()
        logger.info("DSP pipeline initialized")
    
    def analyze(self, filepath: Path) -> Tuple[AudioMetadata, DSPAnalysis, SpectralAnalysis]:
        """
        Run complete DSP analysis pipeline.
        
        Args:
            filepath: Path to audio file
            
        Returns:
            Tuple of (metadata, dsp_analysis, spectral_analysis)
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If file format unsupported
            RuntimeError: If analysis fails
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")
        
        logger.info(f"Starting analysis: {filepath.name}")
        
        try:
            # Extract metadata first (fastest, validates file)
            metadata = self._metadata.extract(filepath)
            logger.debug(f"Metadata: {metadata.codec} @ {metadata.bitrate}kbps")
            
            # Run DSP analysis (time domain)
            dsp_result = self._dsp.analyze(filepath)
            logger.debug(f"DSP: RMS={dsp_result.rms_level_db:.1f}dB, Clipping={dsp_result.clipping_detected}")
            
            # Run spectral analysis (frequency domain)
            spectral_result = self._spectral.analyze(filepath)
            logger.debug(f"Spectral: Cutoff={spectral_result.high_freq_cutoff_khz:.1f}kHz")
            
            logger.info(f"Analysis complete: {filepath.name}")
            return metadata, dsp_result, spectral_result
            
        except Exception as e:
            logger.error(f"Analysis failed for {filepath.name}: {e}", exc_info=True)
            raise RuntimeError(f"DSP pipeline failed: {e}") from e
    
    def validate_file(self, filepath: Path) -> bool:
        """Quick validation without full analysis."""
        return self._metadata.is_supported(filepath)
