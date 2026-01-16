import requests
import json
import logging

class LLMArbitrator:
    def __init__(self, model_name="qwen2.5", host="http://localhost:11434"):
        """Initialise la connexion avec le serveur Ollama local."""
        self.model_name = model_name
        self.api_url = f"{host}/api/generate"
        self.logger = logging.getLogger("AudioExpert.LLM")

    def get_verdict(self, file_path, dsp_data, ml_score):
        """
        Envoie les métriques au LLM pour obtenir une analyse qualitative.
        DSP_DATA contient : clipping, snr, phase, fake_hq, cutoff.
        """
        prompt = self._build_prompt(file_path, dsp_data, ml_score)
        
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = json.loads(response.text)
                return json.loads(result['response'])
            else:
                return self._fallback_verdict("Erreur serveur Ollama")
                
        except Exception as e:
            self.logger.error(f"Échec de l'arbitrage LLM : {e}")
            return self._fallback_verdict(str(e))

    def _build_prompt(self, path, dsp, score):
        """Construit un prompt technique structuré pour Qwen 2.5."""
        return f"""
        En tant qu'expert en ingénierie audio, analyse ces métriques pour le fichier: {path}
        
        MÉTRIQUES :
        - Clipping (Amplitude saturée) : {dsp['clipping']:.2f}%
        - Rapport Signal/Bruit (SNR) : {dsp['snr']:.1f} dB
        - Corrélation de Phase : {dsp['phase']:.2f}
        - Score de suspicion Fake HQ : {dsp['fake_hq']:.2f}
        - Coupure spectrale identifiée : {dsp['cutoff']:.0f} Hz
        - Score de suspicion IA (ML) : {score:.2f}

        INSTRUCTIONS :
        Détermine si le fichier est de qualité "Studio/Original" ou s'il s'agit d'un "Fake/Défectueux".
        Réponds UNIQUEMENT au format JSON suivant :
        {{
            "verdict": "GOOD" ou "BAN",
            "confidence": 0.0 à 1.0,
            "reason": "Explication technique courte en français"
        }}
        """

    def _fallback_verdict(self, error_msg):
        """Réponse de secours en cas de panne du service IA."""
        return {
            "verdict": "PENDING",
            "confidence": 0.0,
            "reason": f"Arbitrage indisponible : {error_msg}"
        }
