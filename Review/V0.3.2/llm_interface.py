"""
Audiopro LLM Provider Interface v0.2.5
- Abstract Base Class (ABC) for arbitration services
- Ensures strict adherence to the Hexagon Core architecture
- Facilitates dependency injection in app.py
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMProvider(ABC):
    """
    Interface definition for all LLM Arbitration services.
    Standardizes the communication contract between the Orchestrator and AI models.
    """

    @abstractmethod
    def arbitrate(self, metrics: Dict[str, Any]) -> str:
        """
        Takes a dictionary of DSP metrics and returns a classification string.
        Must be implemented by any specific provider (e.g., Ollama, OpenAI).
        """
        pass

    def check_health(self) -> bool:
        """
        Optional health check for the service. 
        Defaults to True if not overridden by the provider.
        """
        return True
