"""
Audiopro LLM Provider Interface v0.3.1
- Abstract Base Class (ABC) for arbitration services
- Ensures strict adherence to the Hexagon Core architecture
- Updated: Returns tuple[str, str] for (Verdict, Justification) compliance
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class LLMProvider(ABC):
    """
    Interface definition for all LLM Arbitration services.
    Standardizes the communication contract between the Orchestrator and AI models.
    """

    @abstractmethod
    def arbitrate(self, metrics: Dict[str, Any]) -> Tuple[str, str]:
        """
        Takes a dictionary of DSP metrics and returns a (verdict, justification) tuple.
        Must be implemented by any specific provider (e.g., Ollama, Mock).
        """
        pass

    def check_health(self) -> bool:
        """
        Optional health check for the service. 
        Defaults to True if not overridden by the provider.
        """
        return True
