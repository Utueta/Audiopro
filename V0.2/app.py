import sys
import os
import json
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

# Imports des modules du projet
from view import AudioExpertView
from splash_screen import SplashScreen
from analyzer import AudioAnalyzer
from model import AudioModel
from llm_service import LLMService

class AudioExpertApp:
    def __init__(self):
        # 1. Configuration Initiale & Logging
        self.config_path = "config.json"
        self.config = self._load_config()
        self._setup_logging()

        # 2. Initialisation des Cores (Moteurs)
        # Le Model crée les dossiers database/ et models/ automatiquement
        self.model = AudioModel(self.config)
        self.analyzer = AudioAnalyzer(self.config)
        self.llm = LLMService(self.config)

        # 3. Initialisation de l'Interface
        self.view = AudioExpertView(self.config)
        
        # 4. Connexion des Signaux (Le pont Logique <-> UI)
        self._connect_signals()

    def _load_config(self):
        """Charge et vérifie la présence du fichier de configuration."""
        if not os.path.exists(self.config_path):
            # Création d'une config par défaut si manquante pour éviter le crash
            print(f"CRITICAL: {self.config_path} non trouvé.")
            sys.exit(1)
        with open(self.config_path, "r", encoding='utf-8') as f:
            return json.load(f)

    def _setup_logging(self):
        """Configure le journal de bord dans /logs."""
        log_dir = os.path.dirname(self.config['paths']['log_path'])
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            filename=self.config['paths']['log_path'],
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _connect_signals(self):
        """Établit les communications entre les composants (Design Pattern Observer)."""
        # Quand l'utilisateur demande un scan dans la View
        self.view.scan_requested.connect(self.process_new_scan)
        
        # Charger l'historique récent (JSON) dans la table au démarrage
        recent_data = self.model.get_recent_history()
        self.view.populate_initial_data(recent_data)

    def process_new_scan(self, file_path):
        """Pipeline de traitement : Analyse -> ML -> LLM -> Sauvegarde -> UI."""
        try:
            logging.info(f"Début de l'analyse : {file_path}")
            
            # A. Analyse Physique (DSP)
            metrics = self.analyzer.get_metrics(file_path)
            
            # B. Prédiction Machine Learning
            ml_score = self.model.classifier.predict_proba([self._flatten(metrics)])[0][1]
            
            # C. Arbitrage IA (LLM) si score ambigu (zone d'ombre)
            zone = self.config['llm']['arbitration_zone']
            analysis_text = ""
            if zone['min_score'] <= ml_score <= zone['max_score']:
                analysis_text = self.llm.analyze_anomaly(metrics, ml_score)

            # D. Sauvegarde Hybride (SQL + JSON Cache via le Model)
            self.model.save_analysis(metrics, ml_score)
            
            # E. Mise à jour de l'UI
            self.view.update_result_display(metrics, ml_score, analysis_text)
            
        except Exception as e:
            logging.error(f"Erreur durant le scan de {file_path} : {str(e)}")
            self.view.show_error(f"Erreur de traitement : {os.path.basename(file_path)}")

    def _flatten(self, metrics):
        """Convertit le dictionnaire de métriques en vecteur pour le ML."""
        return [metrics['is_fake_hq'], metrics['clipping'], metrics['snr'], metrics['meta']['bitrate']]

    def run(self):
        """Lance le SplashScreen avant d'afficher l'application principale."""
        splash = SplashScreen(self.config)
        splash.show()
        
        # Exécution des tests de santé (GPU, Ollama, Chemins)
        if splash.run_checks():
            splash.close()
            self.view.show()
        else:
            logging.critical("Échec des tests de santé système. Fermeture.")
            QMessageBox.critical(None, "Erreur Système", 
                                "Les composants requis (GPU ou Ollama) sont introuvables.")
            sys.exit(1)

if __name__ == "__main__":
    # Paramètres haute résolution pour l'interface Obsidian
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Expert Pro")
    
    # Lancement de l'orchestrateur
    core_app = AudioExpertApp()
    core_app.run()
    
    sys.exit(app.exec())
