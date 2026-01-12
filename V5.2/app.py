import os
import json
import sys
from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject
from PySide6.QtWidgets import QApplication

from analyzer import AudioAnalyzer
from model import AudioModel
from llm_service import LLMService
from view import AudioExpertView

# --- Gestionnaire de signaux pour le ThreadPool ---
class AnalysisSignals(QObject):
    result = Signal(dict)
    finished = Signal()
    error = Signal(str)

# --- Tâche d'analyse asynchrone ---
class AnalysisWorker(QRunnable):
    def __init__(self, file_path, analyzer, model, llm):
        super().__init__()
        self.file_path = file_path
        self.analyzer = analyzer
        self.model = model
        self.llm = llm
        self.signals = AnalysisSignals()

    def run(self):
        try:
            # 1. Analyse physique
            metrics = self.analyzer.get_metrics(self.file_path)
            if not metrics:
                return

            # 2. Score ML
            metrics['ml_score'] = self.model.predict_suspicion(metrics)

            # 3. Arbitrage de Zone Grise (Spécification V0.1)
            # Si le score est entre 0.4 et 0.7, on demande au LLM
            zone = self.model.config['llm']['arbitration_zone']
            if zone['min_score'] <= metrics['ml_score'] <= zone['max_score']:
                verdict_llm = self.llm.get_verdict(metrics)
                metrics['llm_decision'] = verdict_llm.get('decision', 'FLAG')
                metrics['llm_reason'] = verdict_llm.get('reason', 'Besoin de révision humaine.')
            else:
                metrics['llm_decision'] = "AUTO"
                metrics['llm_reason'] = "Score ML tranché."

            self.signals.result.emit(metrics)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

# --- Contrôleur Principal ---
class AudioExpertApp:
    def __init__(self):
        self.load_config()
        
        # Initialisation des composants cœurs
        self.analyzer = AudioAnalyzer(self.config)
        self.model = AudioModel()
        self.llm = LLMService(self.config)
        
        # Interface et Threading
        self.view = AudioExpertView(self.config)
        self.threadpool = QThreadPool()
        # Utilise tous les cœurs sauf un pour garder le système réactif
        self.threadpool.setMaxThreadCount(max(1, os.cpu_count() - 1))

        # Connexions Signaux -> Slots
        self.view.scan_requested.connect(self.start_folder_scan)
        self.view.label_submitted.connect(self.process_user_feedback)

    def load_config(self):
        with open("config.json", "r") as f:
            self.config = json.load(f)

    def start_folder_scan(self, folder_path):
        """Parcours récursif et envoi au pool de threads."""
        extensions = self.config['audio']['extensions']
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, file)
                    worker = AnalysisWorker(full_path, self.analyzer, self.model, self.llm)
                    worker.signals.result.connect(self.on_analysis_complete)
                    self.threadpool.start(worker)

    def on_analysis_complete(self, metrics):
        """Traitement du résultat final et mise à jour UI."""
        # Enregistre en base de données (SQLite)
        self.model.add_to_history(metrics)
        
        # Met à jour l'interface graphique
        self.view.add_result_to_table(metrics)
        
        # Gestion intelligente des doublons (Spécification V0.1)
        # On pourrait ici marquer le fichier si un hash identique existe déjà

    def process_user_feedback(self, file_hash, label):
        """Gère le feedback utilisateur pour le réentraînement du modèle."""
        # Récupère les métriques depuis la DB via le hash
        # Met à jour le label (Ban/Good) et déclenche potentiellement le retrain()
        with self.model as m:
            m.mark_user_decision(file_hash, label)

    def run(self):
        self.view.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Expert Pro V0.1")
    
    expert_app = AudioExpertApp()
    expert_app.run()
    
    sys.exit(app.exec())
