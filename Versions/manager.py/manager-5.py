"""
Orchestrator coordinating all subsystems.
Uses dependency injection for testability.
"""
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from .analyzer.pipeline import AudioAnalysisPipeline
from .brain.model_interface import AudioQualityModel
from services.llm_interface import LLMProvider
from persistence.repository import AnalysisRepository
from .models import AnalysisResult, LLMArbitration


logger = logging.getLogger(__name__)


class AnalysisManager:
    """
    Core orchestrator - coordinates DSP, ML, LLM, and persistence.
    All dependencies injected for testability.
    """
    
    def __init__(
        self,
        dsp_pipeline: AudioAnalysisPipeline,
        ml_model: AudioQualityModel,
        llm_provider: LLMProvider,
        repository: AnalysisRepository,
        llm_confidence_threshold: float = 0.85
    ):
        self.dsp_pipeline = dsp_pipeline
        self.ml_model = ml_model
        self.llm_provider = llm_provider
        self.repository = repository
        self.llm_threshold = llm_confidence_threshold
        
        logger.info("AnalysisManager initialized")
    
    def analyze_file(self, filepath: Path) -> AnalysisResult:
        """
        Complete analysis pipeline for single file.
        
        Returns:
            Complete analysis result with final quality verdict
        """
        logger.info(f"Starting analysis: {filepath.name}")
        
        # Phase 1: DSP Analysis
        metadata, dsp, spectral = self.dsp_pipeline.analyze(filepath)
        
        # Phase 2: ML Classification
        ml_classification = self.ml_model.predict(dsp, spectral)
        logger.info(f"ML: {ml_classification.predicted_class} ({ml_classification.confidence:.2%})")
        
        # Phase 3: Conditional LLM Arbitration
        llm_result = None
        if ml_classification.confidence < self.llm_threshold:
            logger.info("Low ML confidence - requesting LLM arbitration")
            
            # Build partial result for LLM
            partial_result = AnalysisResult(
                analysis_id=str(uuid.uuid4()),
                filepath=filepath,
                timestamp=datetime.now(),
                metadata=metadata,
                dsp=dsp,
                spectral=spectral,
                ml_classification=ml_classification,
                llm_arbitration=None,
                final_quality=ml_classification.predicted_class,
                user_feedback=None
            )
            
            llm_result = self.llm_provider.arbitrate(partial_result)
        
        # Phase 4: Final Verdict
        final_quality = self._determine_final_quality(ml_classification, llm_result)
        
        # Build complete result
        result = AnalysisResult(
            analysis_id=str(uuid.uuid4()),
            filepath=filepath,
            timestamp=datetime.now(),
            metadata=metadata,
            dsp=dsp,
            spectral=spectral,
            ml_classification=ml_classification,
            llm_arbitration=llm_result,
            final_quality=final_quality,
            user_feedback=None
        )
        
        # Phase 5: Persist
        self.repository.save(result)
        
        logger.info(f"Analysis complete: {final_quality}")
        return result
    
    def _determine_final_quality(
        self, 
        ml_classification, 
        llm_arbitration: Optional[LLMArbitration]
    ) -> str:
        """
        Determine final quality verdict from ML and LLM results.
        Logic: LLM overrides ML when confidence is low.
        """
        if llm_arbitration:
            return llm_arbitration.recommendation
        return ml_classification.predicted_class
    
    def get_analysis_history(self, filepath: Path) -> Optional[AnalysisResult]:
        """Check if file was previously analyzed."""
        return self.repository.get_by_filepath(filepath)
    
    def submit_feedback(self, analysis_id: str, feedback: str) -> None:
        """Record user feedback for incremental learning."""
        self.repository.update_feedback(analysis_id, feedback)
        logger.info(f"Feedback recorded: {analysis_id}")
