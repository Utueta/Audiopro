import os
import json
import logging
import requests
from datetime import datetime

class LLMArbitrator:
    """
    Service d'arbitrage par IA (Ollama / Qwen 2.5).
    Restaure la capacité de décision intelligente pour les zones grises.
    """
    def __init__(self, model_name="qwen2.5:7b", api_url="http://localhost:11434/api/generate"):
        self.logger = logging.getLogger("Audiopro.LLM")
        self.model_name = model_name
        self.api_url = api_url
        self.timeout = 15  # Protection contre les freezes système

    def arbitrate(self, dsp_data, metadata, ml_score):
        """
        Demande un verdict argumenté au LLM en croisant toutes les métriques.
        Plus-value : Analyse logique des incohérences (ex: Upsampling).
        """
        prompt = self._build_expert_prompt(dsp_data, metadata, ml_score)
        
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json" # Force Qwen à répondre en JSON structuré
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Parsing de la réponse structurée
            verdict_data = json.loads(result.get("response", "{}"))
            
            self.logger.info(f"Arbitrage LLM rendu : {verdict_data.get('verdict')}")
            return verdict_data.get("verdict", "INCONCLUSIVE"), verdict_data.get("reason", "No reason provided")

        except Exception as e:
            self.logger.error(f"Échec de l'arbitrage LLM : {str(e)}")
            # Fallback de sécurité : on suit le score ML si l'IA est hors-ligne
            return ("BAN" if ml_score > 0.7 else "GOOD"), "Fallback: LLM Offline"

    def _build_expert_prompt(self, dsp, meta, score):
        """
        Construit un prompt d'ingénierie pour transformer le LLM en auditeur audio.
        """
        return f"""
        En tant qu'expert en certification audio numérique, analyse ces données :
        
        [METADATA]
        - Format : {meta.get('format_internal')}
        - Bitrate annoncé : {meta.get('bitrate')} kbps
        - Is Lossless : {meta.get('is_lossless')}
        - Is Spoofed (Header mismatch) : {meta.get('is_spoofed')}
        
        [SIGNAL DSP]
        - Cutoff Spectral : {dsp.get('spectral_cutoff')} Hz
        - Clipping : {dsp.get('clipping')}%
        - Corrélation de Phase : {dsp.get('phase_corr')}
        - SNR : {dsp.get('snr')} dB
        
        [MACHINE LEARNING]
        - Score de suspicion : {score:.2f} (1.0 = Fraude certaine)
        
        INSTRUCTIONS :
        1. Si le Bitrate est élevé (>1000) mais le Cutoff est bas (<17000Hz), conclus à un UPSAMPLING (BAN).
        2. Si is_spoofed est True, conclus à une FRAUDE DE CONTENEUR (BAN).
        3. Réponds UNIQUEMENT au format JSON suivant :
        {{
            "verdict": "GOOD" ou "BAN",
            "reason": "Explication technique courte",
            "confidence": 0.0 à 1.0
        }}
        """

    def generate_report_comment(self, result_data):
        """Génère un commentaire professionnel pour le rapport de certification final."""
        # Logique pour créer une synthèse textuelle pour l'utilisateur final
        pass
