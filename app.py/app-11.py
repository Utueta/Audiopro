import sys
import os
import json
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QThreadPool

from view import AudioExpertView
from splash_screen import SplashScreen
from analyzer import AudioAnalyzer
from model import FraudModel
from services.llm_service import LLMService
from workers import AnalysisWorker

class AudioExpertApp:
    def __init__(self):
        self.config_path = "config.json"
        self.config = self._load_config()
        self._setup_logging()

        # Initialisation des Moteurs
        self.analyzer = AudioAnalyzer(self.config)
        self.model = FraudModel(self.config)
        self.llm = LLMService(self.config)

        # Threading & Performance
        self.threadpool = QThreadPool()
        max_t = self.config.get('performance', {}).get('max_threads', 4)
        self.threadpool.setMaxThreadCount(max_t)

        self.view = AudioExpertView(self.config)
        self._connect_signals()

    def _load_config(self):
        if not os.path.exists(self.config_path):
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
        self.view.scan_requested.connect(self.dispatch_worker)
        self.view.feedback_given.connect(self.model.update_feedback)

    def dispatch_worker(self, file_path):
        logging.info(f"Analyse lancée : {file_path}")
        worker = AnalysisWorker(file_path, self.analyzer, self.model, self.llm)
        
        # Axe A : Flux de signaux asynchrones
        worker.signals.dsp_ready.connect(self.view.handle_dsp_ready)
        worker.signals.result.connect(self.on_analysis_finished)
        worker.signals.error.connect(lambda e: logging.error(f"Erreur Worker: {e}"))
        
        self.threadpool.start(worker)

    def on_analysis_finished(self, results):
        self.view.handle_analysis_result(results)
        self.model.save_analysis(results, results['score'])
        logging.info(f"Analyse terminée : {results['filename']}")

    def run(self):
        splash = SplashScreen(self.config)
        splash.show()
        if splash.run_checks():
            splash.close()
            self.view.show()
        else:
            QMessageBox.critical(None, "System Error", "Échec des tests de santé (Ollama/Dossiers).")
            sys.exit(1)

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    core = AudioExpertApp()
    core.run()
    sys.exit(app.exec())
