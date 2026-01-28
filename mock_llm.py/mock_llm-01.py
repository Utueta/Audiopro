"""
Audiopro Mock LLM Service v0.3.1
- Stateless stub for CI/CD.
- Updated to return (Verdict, Justification) tuple.
"""
from services.llm_interface import LLMProvider

class MockLLM(LLMProvider):
    def arbitrate(self, result_data: dict) -> tuple[str, str]:
        suspicion = result_data.get("suspicion_score", 0.0)
        if suspicion > 0.75:
            return "CORRUPT", "Mock: High suspicion triggers corruption verdict."
        return "CLEAN", "Mock: DSP metrics within normal bounds."
