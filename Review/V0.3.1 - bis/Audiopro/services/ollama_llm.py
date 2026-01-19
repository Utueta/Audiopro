"""
Audiopro Robust LLM Service v0.3.1
- Merged Architecture: Interface-compliant + String-reliable
- v0.3.1: Returns tuple (Verdict, Justification) for database enrichment.
"""

import requests
import logging
from services.llm_interface import LLMProvider

logger = logging.getLogger("system.services.llm")

class OllamaBridge(LLMProvider):
    def __init__(self, url="http://localhost:11434/api/generate", model="qwen2.5"):
        self.url = url
        self.model = model

    def arbitrate(self, result_data: dict) -> tuple[str, str]:
        """Sends DSP metrics to LLM for final forensic decision."""
        prompt = (
            f"Act as an Expert Audio Forensic Engineer. Analyze these metrics:\n"
            f"SNR: {result_data.get('snr')}dB, Clipping: {result_data.get('clipping')} samples.\n"
            f"Explain your reasoning then conclude with ONLY the word CLEAN or CORRUPT."
        )

        payload = {
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 150}
        }

        try:
            response = requests.post(self.url, json=payload, timeout=15)
            response.raise_for_status()
            full_text = response.json().get("response", "").strip()
            
            verdict = "REVIEW_REQUIRED"
            if "CLEAN" in full_text.upper(): verdict = "CLEAN"
            elif "CORRUPT" in full_text.upper(): verdict = "CORRUPT"
            
            return verdict, full_text
        except Exception as e:
            logger.error(f"LLM Connection Failed: {e}")
            return "ERROR", str(e)
