import sys
import os
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QThreadPool, Slot, QObject

# Modules consolidés (issus du buffer actif)
from core.manager import CentralManager
from ui.view import AudioAnalysisView
from ui.components.splash import ObsidianSplashScreen
from core.workers import AnalysisWorker 

class AudioproController(QObject):
    """
    Contrôleur de Certification (MVC).
    Lien dynamique entre l'UI Obsidian Glow et le moteur asynchrone.
    """
    def __init__(self):
        super().__init__()
        self._setup_logging()
        self.logger = logging.getLogger("Audiopro.Controller")
        
        # 1. Initialisation du moteur (Core)
        self.manager = CentralManager()
        
        # 2. Gestionnaire de Threads haute performance
        self.threadpool = QThreadPool()
        # DevSecOps : Limitation pour éviter l'épuisement des ressources sur Fedora
        self.threadpool.setMaxThreadCount(max(2, os.cpu_count() or 4))
        
        # 3. Préparation de la Vue
        self.view = AudioAnalysisView(self.manager)
        
        # 4. Connexion des signaux (Liaison UI-Logic)
        self.view.request_scan.connect(self.start_analysis)
        self.view.request_action.connect(self.handle_feedback)

    def _setup_logging(self):
        os.makedirs("logs", exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[logging.FileHandler("logs/controller.log"), logging.StreamHandler()]
        )

    @Slot(str)
    def start_analysis(self, path):
        """
        Point d'entrée unique pour Drag & Drop ou Sélection manuelle.
        Gère intelligemment fichiers et répertoires.
        """
        supported = ('.flac', '.wav', '.mp3', '.aiff', '.m4a')
        files_to_process = []

        if os.path.isdir(path):
            self.logger.info(f"Scan de répertoire détecté : {path}")
            files_to_process = [os.path.join(path, f) for f in os.listdir(path) 
                                if f.lower().endswith(supported)]
        elif os.path.isfile(path) and path.lower().endswith(supported):
            self.logger.info(f"Fichier unique détecté : {path}")
            files_to_process = [path]

        if not files_to_process:
            self.view.console.append("<span style='color: #FF0055;'>[!] Aucun fichier audio compatible trouvé.</span>")
            return

        # Configuration de la progression
        self.view.progress_bar.setMaximum(len(files_to_process))
        self.view.progress_bar.setValue(0)
        self.view.progress_bar.show()
        self.view.status_label.setText(f"ANALYSE DE {len(files_to_process)} ÉLÉMENT(S)...")

        # Distribution dans le ThreadPool
        for file_path in files_to_process:
            worker = AnalysisWorker(self.manager, file_path)
            # Connexion des signaux du worker vers le contrôleur
            worker.signals.result.connect(self._on_item_finished)
            worker.signals.error.connect(lambda m: self.logger.error(f"Worker Error: {m}"))
            self.threadpool.start(worker)

    @Slot(dict)
    def _on_item_finished(self, result):
        """Mise à jour thread-safe de l'UI Obsidian suite à une analyse."""
        self.view.update_ui_with_results(result)
        
        current_val = self.view.progress_bar.value()
        new_val = current_val + 1
        self.view.progress_bar.setValue(new_val)
        
        # Si le batch est fini
        if new_val >= self.view.progress_bar.maximum():
            self.view.status_label.setText("BATCH TERMINÉ")
            self.view.progress_bar.hide()
            self.logger.info("Batch d'analyse terminé avec succès.")

    @Slot(str, str)
    def handle_feedback(self, file_hash, action):
        """Feedback loop pour l'apprentissage du Brain (ML)."""
        self.logger.info(f"Feedback expert : {action} pour {file_hash}")
        self.manager.apply_human_feedback(file_hash, action)
        self.view.console.append(f"<span style='color: #00F2FF;'>[BRAIN] Feedback '{action}' enregistré.</span>")

def main():
    # Fix pour les écrans High DPI (Standard V5)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Audiopro Expert Certification")

    # Instance du Contrôleur (MVC)
    controller = AudioproController()

    # Orchestration du lancement
    def launch_sequence():
        controller.view.show()
        splash.close()

    # SplashScreen Obsidian Glow
    splash = ObsidianSplashScreen(on_complete_callback=launch_sequence)
    splash.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
