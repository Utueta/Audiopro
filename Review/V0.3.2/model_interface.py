from typing import Protocol, Tuple
import numpy as np

class MLModelInterface(Protocol):
    """Protocol for audio classification models."""
    def classify(self, snr: float, clipping: int, suspicion: float) -> Tuple[str, float]:
        ...
        
    def save_weights(self, path: str) -> None:
        ...
