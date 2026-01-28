"""
Protocol for LLM providers.
Enables testing without Ollama and future provider swapping.
"""
from typing import Protocol
from core.models import AnalysisResult, LLMArbitration


class LLMProvider(Protocol):
    """Interface for LLM arbitration services."""
    
    def arbitrate(self, analysis: AnalysisResult) -> LLMArbitration:
        """
        Request LLM arbitration for edge cases.
        
        Args:
            analysis: Complete analysis result needing arbitration
            
        Returns:
            LLM recommendation with reasoning
        """
        ...
    
    def health_check(self) -> bool:
        """Check if LLM service is available."""
        ...
    
    def get_provider_info(self) -> dict:
        """Return provider name and model info."""
        ...
