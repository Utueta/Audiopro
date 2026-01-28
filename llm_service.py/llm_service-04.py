import requests

class LLMService:
    def __init__(self, config):
        self.cfg = config['llm']

    def check_arbitration(self, score):
        return self.cfg['arbitration_zone']['min_score'] <= score <= self.cfg['arbitration_zone']['max_score']

    def analyze_anomaly(self, metrics):
        try:
            res = requests.post(self.cfg['api_url'], json={
                "model": self.cfg['model_name'],
                "prompt": f"Audit Audio: {metrics['filename']} score {metrics['score']:.2f}. Clipping {metrics['clipping']:.4f}. Verdict?",
                "stream": False
            }, timeout=15)
            return res.json().get('response', "IA occupée.")
        except:
            return "Ollama Offline."
