"""
Ollama implementation of LLM provider.
"""
import requests
import logging
from datetime import datetime
from typing import Optional

from .llm_interface import LLMProvider
from core.models import AnalysisResult, LLMArbitration


logger = logging.getLogger(__name__)


class OllamaLLM:
    """Ollama / Qwen 2.5 LLM arbitration service."""
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.model_name = "qwen2.5:7b-instruct"
    
    def arbitrate(self, analysis: AnalysisResult) -> LLMArbitration:
        """Implement protocol method."""
        
        # Build prompt from analysis result
        prompt = self._build_prompt(analysis)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            recommendation = self._parse_response(result['response'])
            
            logger.info(f"LLM arbitration: {recommendation['verdict']}")
            
            return LLMArbitration(
                recommendation=recommendation['verdict'],
                reasoning=recommendation['reasoning'],
                confidence_override=recommendation.get('confidence'),
                timestamp=datetime.now()
            )
            
        except requests.Timeout:
            logger.error("LLM request timeout")
            return self._fallback_arbitration("LLM timeout")
            
        except Exception as e:
            logger.error(f"LLM arbitration failed: {e}")
            return self._fallback_arbitration(f"LLM error: {e}")
    
    def _build_prompt(self, analysis: AnalysisResult) -> str:
        """Construct arbitration prompt from analysis data."""
        return f"""You are an expert audio engineer. Analyze this audio file quality assessment:

File: {analysis.filepath.name}
ML Prediction: {analysis.ml_classification.predicted_class} (confidence: {analysis.ml_classification.confidence:.2%})

Technical Metrics:
- RMS Level: {analysis.dsp.rms_level_db:.1f} dB
- Dynamic Range: {analysis.dsp.dynamic_range_db:.1f} dB
- Clipping Detected: {analysis.dsp.clipping_detected}
- Frequency Cutoff: {analysis.spectral.high_freq_cutoff_khz:.1f} kHz
- Bitrate: {analysis.metadata.bitrate} kbps
- Codec: {analysis.metadata.codec}

The ML model shows moderate confidence. Provide your expert arbitration:
1. Do you agree with the ML classification?
2. What's your reasoning based on the metrics?
3. Final quality verdict: excellent/good/acceptable/poor/needs_review

Format: JSON with keys: verdict, reasoning, confidence (0-1)"""
    
    def _parse_response(self, response_text: str) -> dict:
        """Extract structured data from LLM response."""
        # Parse JSON or extract from text
        # Implementation depends on Qwen response format
        pass
    
    def _fallback_arbitration(self, reason: str) -> LLMArbitration:
        """Return safe fallback when LLM unavailable."""
        return LLMArbitration(
            recommendation="needs_review",
            reasoning=f"LLM unavailable: {reason}. Manual review recommended.",
            confidence_override=None,
            timestamp=datetime.now()
        )
    
    def health_check(self) -> bool:
        """Implement protocol method."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_provider_info(self) -> dict:
        """Implement protocol method."""
        return {
            'provider': 'Ollama',
            'model': self.model_name,
            'url': self.base_url
        }
