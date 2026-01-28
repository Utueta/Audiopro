"""
Mock LLM for testing without Ollama dependency.
"""
from datetime import datetime
from .llm_interface import LLMProvider
from core.models import AnalysisResult, LLMArbitration


class MockLLM:
    """Testing stub - always agrees with ML classification."""
    
    def arbitrate(self, analysis: AnalysisResult) -> LLMArbitration:
        """Return mock arbitration based on ML confidence."""
        ml = analysis.ml_classification
        
        if ml.confidence > 0.8:
            verdict = ml.predicted_class
            reasoning = f"High ML confidence ({ml.confidence:.2%}). Classification validated."
        else:
            verdict = "needs_review"
            reasoning = f"Low ML confidence ({ml.confidence:.2%}). Manual review recommended."
        
        return LLMArbitration(
            recommendation=verdict,
            reasoning=reasoning,
            confidence_override=None,
            timestamp=datetime.now()
        )
    
    def health_check(self) -> bool:
        return True
    
    def get_provider_info(self) -> dict:
        return {'provider': 'Mock', 'model': 'test_stub'}
