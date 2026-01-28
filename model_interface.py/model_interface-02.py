"""
Audiopro v0.3.1
Handles the abstract definition for all ML model implementations.
"""
from abc import ABC, abstractmethod
from core.models import AnalysisResult

class ModelInterface(ABC):
    @abstractmethod
    def predict(self, result: AnalysisResult) -> float:
        """Returns a normalized suspicion score [0.0 - 1.0]."""
        pass
