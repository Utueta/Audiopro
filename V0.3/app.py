import sys
import os
import json
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QThreadPool

# Imports des modules
from view import AudioExpertView
from splash_screen import SplashScreen
from analyzer import AudioAnalyzer
from model import FraudModel
from services.llm_service import LLMService
from workers import AnalysisWorker

class AudioExpertApp:
    def __init__(self):
        # 1. Configuration & Logs (Ancienne logique restaurée)
        self.config_path = "config.json"
        self.config = self._load_config()
        self._setup_logging()

        # 2. Initialisation des Moteurs
        self.analyzer = AudioAnalyzer(self.config)
        self.model = FraudModel(self.config)
        self.llm = LLMService(self.config)

        # 3. ThreadPool (Nouvelle performance V0.2.4)
        self.threadpool = QThreadPool()
        max_t = self.config.get('performance', {}).get('max_threads', 4)
        self.threadpool.setMaxThreadCount(max_t)

        # 4. Interface (Sera affichée par run())
        self.view = AudioExpertView(self.config)
        self._connect_signals()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            print(f"CRITICAL: {self.config_path} manquant.")
            sys.exit(1)
        with open(self.config_path, "r", encoding='utf-8') as f:
            return json.load(f)

    def _setup_logging(self):
        log_path = self.config['paths']['log_path']
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _connect_signals(self):
        # Signal de la vue (Drag & Drop ou Bouton) -> Lancement Thread
        self.view.scan_requested.connect(self.dispatch_worker)

    def dispatch_worker(self, file_path):
        """Prépare et lance le travail en arrière-plan."""
        logging.info(f"Assignation thread pour : {file_path}")
        
        # On passe le LLM au worker pour l'arbitrage asynchrone
        worker = AnalysisWorker(file_path, self.analyzer, self.model, self.llm)
        
        # Connexion des retours
        worker.signals.result.connect(self.on_analysis_finished)
        worker.signals.error.connect(lambda e: logging.error(f"Thread Error: {e}"))
        
        self.threadpool.start(worker)

    def on_analysis_finished(self, results):
        """Mise à jour de l'UI une fois le thread terminé."""
        # On délègue l'affichage final à la vue (Glow, Table, Zoom)
        self.view.handle_analysis_result(results)
        logging.info(f"Analyse terminée avec succès : {results['filename']}")

    def run(self):
        """Logique du SplashScreen (Ancienne logique restaurée)."""
        splash = SplashScreen(self.config)
        splash.show()
        
        if splash.run_checks():
            splash.close()
            self.view.show()
            logging.info("Application démarrée avec succès après check-up.")
        else:
            logging.critical("Échec des tests système au démarrage.")
            QMessageBox.critical(None, "Erreur Système", "Composants requis introuvables.")
            sys.exit(1)

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Expert Pro")
    
    core = AudioExpertApp()
    core.run()
    
    sys.exit(app.exec())
