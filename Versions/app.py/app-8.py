import sys
import os
import json
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QThreadPool

# --- Nouveaux Imports (Structure V0.2.4) ---
from ui.view import AudioExpertView
from splash_screen import SplashScreen
from analyzer import AudioAnalyzer
from model import FraudModel
from services.llm_service import LLMService
from workers import AnalysisWorker

class AudioExpertApp:
    def __init__(self):
        """Initialisation du Core, des Moteurs et de l'Interface."""
        # 1. Configuration & Journalisation
        self.config_path = "config.json"
        self.config = self._load_config()
        self._setup_logging()

        # 2. Initialisation des Moteurs (DSP, ML, LLM)
        self.analyzer = AudioAnalyzer(self.config)
        self.model = FraudModel(self.config)
        self.llm = LLMService(self.config)

        # 3. Gestionnaire de Multi-threading
        self.threadpool = QThreadPool()
        # On limite le nombre de threads selon la config (défaut 4)
        max_t = self.config.get('performance', {}).get('max_threads', 4)
        self.threadpool.setMaxThreadCount(max_t)
        logging.info(f"Threadpool prêt : {max_t} threads max.")

        # 4. Interface Utilisateur (Dashboard Obsidian)
        self.view = AudioExpertView(self.config)
        self._connect_signals()

    def _load_config(self):
        """Charge le fichier de configuration central."""
        if not os.path.exists(self.config_path):
            print(f"CRITICAL: {self.config_path} introuvable.")
            sys.exit(1)
        with open(self.config_path, "r", encoding='utf-8') as f:
            return json.load(f)

    def _setup_logging(self):
        """Configure le journal d'audit."""
        log_file = self.config['paths'].get('log_path', 'logs/session.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _connect_signals(self):
        """Relie les interactions de la vue aux actions du contrôleur."""
        # Connexion du signal de drop de fichier de la vue vers le lanceur d'analyse
        self.view.file_dropped.connect(self.launch_analysis)

    def launch_analysis(self, file_path):
        """Instancie un Worker pour analyser le fichier en arrière-plan."""
        logging.info(f"Préparation de l'analyse : {file_path}")
        
        # Création du travailleur (Worker)
        worker = AnalysisWorker(file_path, self.analyzer, self.model, self.llm)
        
        # Connexion des signaux du thread vers l'interface
        worker.signals.result.connect(self.on_analysis_finished)
        worker.signals.error.connect(lambda e: logging.error(f"Erreur de calcul : {e}"))
        
        # Lancement immédiat sans bloquer l'UI
        self.threadpool.start(worker)

    def on_analysis_finished(self, results):
        """Réception des résultats et mise à jour de l'interface."""
        # On délègue l'affichage final (Glow, Texte, Graphes) à la vue
        self.view.handle_analysis_result(results)
        logging.info(f"Résultats affichés pour : {os.path.basename(results['path'])}")

    def run(self):
        """Lance la séquence de démarrage (Splash -> Main UI)."""
        # 1. Écran de démarrage avec diagnostics
        splash = SplashScreen(self.config)
        splash.show()
        
        # 2. Exécution des checks de santé (CUDA, FFmpeg, Ollama)
        if splash.run_checks():
            logging.info("Diagnostics réussis. Ouverture du dashboard.")
            splash.close()
            self.view.show()
        else:
            logging.critical("Échec des tests système au démarrage.")
            QMessageBox.critical(None, "Échec Diagnostic", 
                               "Certains composants critiques sont manquants.\n"
                               "Consultez logs/session.log pour plus de détails.")
            sys.exit(1)

if __name__ == "__main__":
    # Support de la haute résolution (DPI)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Expert Pro V0.2.4")
    
    # Démarrage de l'orchestrateur
    core = AudioExpertApp()
    core.run()
    
    sys.exit(app.exec())
