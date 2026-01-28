"""
Audiopro Robust LLM Service v0.3.1
- Merged Architecture: Interface-compliant + String-reliable
- High Determinism: Temperature 0.1 (Merged from v0.2.6)
- Role-based Technical Logic: Forensic Audio Expert
"""

import requests
import logging
from services.llm_interface import LLMProvider

logger = logging.getLogger("system.services.llm")

class OllamaBridge(LLMProvider):
    def __init__(self, url="http://localhost:11434/api/generate", model="qwen2.5"):
        self.url = url
        self.model = model

    def arbitrate(self, data: dict) -> str:
        """
        Sends DSP metrics to LLM for final forensic decision.
        Uses string-matching for reliability against formatting quirks.
        """
        prompt = (
            f"Act as an Expert Audio Forensic Engineer. Analyze these metrics:\n"
            f"SNR: {data.get('snr')}dB, Clipping: {data.get('clipping')} samples.\n"
            f"Return ONLY one word: CLEAN or CORRUPT."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Merged: Enforces deterministic response
                "num_predict": 10    # Short response to optimize GPU/latency
            }
        }

        try:
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            
            # Extract and sanitize string response (Robustness Merge)
            raw_text = response.json().get("response", "").strip().upper()
            
            if "CLEAN" in raw_text: return "CLEAN"
            if "CORRUPT" in raw_text: return "CORRUPT"
            
            return "REVIEW_REQUIRED"
        except Exception as e:
            logger.error(f"LLM Bridge Failure: {e}")
            return "REVIEW_REQUIRED"
