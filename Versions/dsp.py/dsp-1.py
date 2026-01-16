import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from core.manager import CentralManager
from ui.view import AudioExpertView

# Configuration du logging pour voir les étapes dans le terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AppController:
    def __init__(self):
        # 1. Définition des chemins de base
        # On s'assure que les dossiers 'data' et 'core/brain' existent
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.base_dir, "data", "inventory.db")
        self.model_path = os.path.join(self.base_dir, "core", "brain", "trained_model.joblib")
        
        # Création du dossier data s'il est manquant
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # 2. Paramètres de configuration
        self.config = {
            "threshold_suspicion": 0.7,
            "llm_enabled": True,
            "theme": "obsidian"
        }

        # 3. Initialisation du Manager (Backend technique)
        # On lui passe les chemins pour SQLite et le modèle ML
        self.manager = CentralManager(
            db_path=self.db_path,
            model_path=self.model_path,
            config=self.config
        )

        # 4. Initialisation de la Vue (Frontend)
        # On injecte le manager dans la vue pour les accès directs (ex: dessin spectrogramme)
        self.view = AudioExpertView(manager=self.manager)
        
        # 5. Connexion des Signaux
        # Si la vue émet 'request_scan', le contrôleur lance la procédure
        # Note: La vue v2.7 gère maintenant son propre Thread interne pour le scan
        # mais le signal 'request_scan' reste utile pour la modularité.
        if hasattr(self.view, 'request_scan'):
            self.view.request_scan.connect(self.handle_scan_request)

        # 6. Affichage final
        self.view.show()

    def handle_scan_request(self, folder_path):
        """Déclenche le scan de dossier via l'interface."""
        logging.info(f"Démarrage du scan demandé pour : {folder_path}")
        # On appelle la méthode de thread de la vue v2.7
        self.view._start_scan(folder_path)

def main():
    # Initialisation de l'application Qt
    app = QApplication(sys.argv)
    
    # Utilisation du style 'Fusion' pour une cohérence cross-platform sur Fedora/Linux
    app.setStyle("Fusion")
    
    # Lancement du contrôleur
    try:
        controller = AppController()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Erreur fatale au lancement de l'application : {e}")

if __name__ == "__main__":
    main()
