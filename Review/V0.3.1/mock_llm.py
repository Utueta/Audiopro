"""
Audiopro Mock LLM Service v0.2.5
- Stateless stub for CI/CD and unit testing
- Implements LLMProvider protocol
- Deterministic responses based on input metrics
"""

import logging
from typing import Dict, Any
from services.llm_interface import LLMProvider

# Segmented Logging: System traces for infrastructure
system_logger = logging.getLogger("system")

class MockLLM(LLMProvider):
    """
    Testing stub that simulates Ollama/Qwen 2.5 responses.
    Allows for full pipeline testing in environments without GPU acceleration.
    """
    def __init__(self, fail_mode: bool = False):
        self.fail_mode = fail_mode

    def arbitrate(self, file_name: str, dsp_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a deterministic verdict based on the suspicion_score.
        Mimics the JSON format expected by the Orchestrator.
        """
        if self.fail_mode:
            system_logger.error(f"Simulated LLM Failure for: {file_name}")
            return {"verdict": "ERROR", "reason": "MOCK_FAIL_MODE_ACTIVE"}

        suspicion = dsp_metrics.get("suspicion_score", 0.0)
        
        # Deterministic Logic for Testing
        if suspicion > 0.8:
            return {
                "verdict": "CORRUPT",
                "reason": "Mock LLM: High spectral suspicion confirms frequency capping."
            }
        
        return {
            "verdict": "CLEAN",
            "reason": "Mock LLM: DSP metrics within nominal range for high-fidelity audio."
        }
