import requests, os
from PySide6.QtCore import QThread, Signal

class LLMService(QThread):
    verdict_ready = Signal(str)

    def __init__(self, config, files_to_review, top_n=10):
        super().__init__()
        self.config = config
        self.files = files_to_review
        self.top_n = top_n

    def run(self):
        # Création du tableau structuré pour le pipeline hiérarchique
        table = [{"id": i, "ml": f['score'], "snr": f['snr']} for i, f in enumerate(self.files) if f['status'] == 'ok']
        
        prompt = (f"Analyze these audio metrics: {table}\n"
                  f"Select {self.top_n} most suspicious.\n"
                  "Output strictly format: id:score, id:score\n"
                  "No text. Only numbers and colons.")

        try:
            r = requests.post(self.config['ia']['llm_url'], 
                             json={"model": self.config['ia']['model_name'], "prompt": prompt, "stream": False},
                             timeout=45)
            self.verdict_ready.emit(r.json().get('response', "").strip())
        except:
            self.verdict_ready.emit("Error:LLM_Offline")
