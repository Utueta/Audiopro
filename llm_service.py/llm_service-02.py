
import requests


class LLMService:

    def __init__(self, config):

        self.cfg = config['llm']


    def check_arbitration(self, score):

        z = self.cfg['arbitration_zone']

        return z['min_score'] <= score <= z['max_score']


    def analyze_anomaly(self, metrics):

        try:

            res = requests.post(self.cfg['api_url'], json={

                "model": self.cfg['model_name'],

                "prompt": f"Audit audio expert : {metrics['filename']}. Score de suspicion {metrics['score']:.2f}. Clipping {metrics['clipping']:.4f}. Rédige un diagnostic court.",

                "stream": False

            }, timeout=15)

            return res.json().get('response', "IA occupée.")

        except: return "Ollama déconnecté."

