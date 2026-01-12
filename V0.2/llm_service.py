import requests
import json

class LLMService:
    def __init__(self, config):
        """Initialisation via le fichier config.json."""
        self.url = config['llm']['api_url']
        self.model = config['llm']['model_name']

    def get_verdict(self, audio_data):
        """
        Analyse les rapports techniques complexes pour fournir un verdict 
        rédigé sur les fichiers ambigus (la 'zone grise').
        """
        prompt = self._build_prompt(audio_data)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3 # Faible température pour plus de précision technique
            }
        }

        try:
            response = requests.post(self.url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Verdict indisponible.")
            else:
                return f"Erreur LLM : Code {response.status_code}"
        except requests.exceptions.ConnectionError:
            return "Ollama non détecté. Lancez 'ollama run qwen2.5'."
        except Exception as e:
            return f"Erreur service IA : {str(e)}"

    def _build_prompt(self, d):
        """Construit le contexte technique pour l'IA."""
        return f"""
        Tu es un expert en ingénierie audio numérique. Analyse les métriques suivantes :
        - Fichier : {d['path']}
        - Bitrate annoncé : {d['meta']['bitrate']} kbps
        - Score de suspicion : {d['score']:.2f}/1.0
        - Clipping (Saturation) : {d['clipping']:.4f}
        - SNR (Bruit) : {d['snr']:.2f} dB
        - Fake HQ (Detection Spectral) : {"OUI" if d['is_fake_hq'] else "NON"}
        - Corrélation Phase : {d['phase_corr']:.2f}

        Donne un verdict court (2 phrases max) sur la qualité réelle de ce fichier.
        Si Fake HQ est à OUI, sois très sévère.
        """
