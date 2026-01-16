import requests

class LLMService:
    def __init__(self, config):
        self.cfg = config['llm']

    def check_arbitration(self, score):
        z = self.cfg['arbitration_zone']
        return z['min_score'] <= score <= z['max_score']

    def analyze_anomaly(self, m):
        try:
            prompt = f"Expert Audit: {m['filename']}. Score {m['score']:.2f}. Clipping {m['clipping']:.4f}. Rédige un diagnostic court."
            res = requests.post(self.cfg['api_url'], json={
                "model": self.cfg['model_name'], "prompt": prompt, "stream": False
            }, timeout=15)
            return res.json().get('response', "IA Indisponible.")
        except: return "Ollama Déconnecté."

