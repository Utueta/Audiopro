"""
Audiopro v0.3.1
Handles the abstract definition for all ML model implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class ModelInterface(ABC):
    @abstractmethod
    def predict(self, features: Dict[str, Any]) -> float:
        """Returns a normalized suspicion score [0.0 - 1.0]."""
        pass

    @abstractmethod
    def load(self, path: str):
        """Loads persistent model artifacts."""
        pass

    @abstractmethod
    def save(self, path: str):
        """Persists model weights."""
        pass
