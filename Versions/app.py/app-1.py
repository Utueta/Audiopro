import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject, Slot

# Importation de nos modules consolidés
from ui.view import AudioExpertView
from core.manager import CentralManager
from workers import AnalysisWorker # Nécessite un petit wrapper QRunnable

class AppController(QObject):
    def __init__(self):
        super().__init__()
        
        # 1. Configuration et Initialisation du Core
        self.config = {
            "db_path": "database/audio_expert.db",
            "model_path": "models/audio_expert_rf.joblib"
        }
        
        # Initialisation du Manager (WAL, RAM Safety, ML)
        self.manager = CentralManager(
            db_path=self.config["db_path"],
            model_path=self.config["model_path"],
            config=self.config
        )
        
        # 2. Initialisation de la Vue
        self.view = AudioExpertView()
        
        # 3. Gestionnaire de Threads
        self.threadpool = QThreadPool()
        # On limite le nombre de threads pour préserver la stabilité (CPU/RAM)
        self.threadpool.setMaxThreadCount(os.cpu_count() or 4)
        
        # 4. Connexion des Signaux (La "Colle")
        self.view.request_scan.connect(self.start_folder_scan)
        self.view.request_action.connect(self.handle_user_decision)

    def start_folder_scan(self, folder_path):
        """Déclenche l'analyse asynchrone de tous les fichiers du dossier."""
        supported_ext = ('.flac', '.wav', '.mp3', '.m4a', '.aiff')
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                 if f.lower().endswith(supported_ext)]
        
        if not files:
            self.view.log_output.setText("Aucun fichier audio supporté trouvé.")
            return

        self.view.progress_bar.setMaximum(len(files))
        self.view.progress_bar.setValue(0)
        
        for file_path in files:
            worker = AnalysisWorker(self.manager, file_path)
            worker.signals.result.connect(self.on_analysis_finished)
            worker.signals.error.connect(lambda msg: print(f"Erreur : {msg}"))
            self.threadpool.start(worker)

    @Slot(dict)
    def on_analysis_finished(self, result):
        """Réception des données du Manager et mise à jour de l'UI."""
        if result["status"] == "SUCCESS":
            self.view.update_results(result)
            self.view.progress_bar.setValue(self.view.progress_bar.value() + 1)
        elif result["status"] == "SKIPPED":
            # On met à jour quand même la progression pour les fichiers déjà connus
            self.view.progress_bar.setValue(self.view.progress_bar.value() + 1)

    @Slot(str, str)
    def handle_user_decision(self, file_hash, action):
        """Transmet le feedback humain au cerveau (ML) pour réentraînement."""
        # Récupération des données en base pour le feedback
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT clipping, snr, phase_corr, fake_hq_score FROM inventory WHERE hash=?", (file_hash,))
        row = cursor.fetchone()
        
        if row:
            features = {
                "clipping": row[0], "snr": row[1], 
                "phase": row[2], "fake_hq": row[3]
            }
            label = 1.0 if action == "BAN" else 0.0
            self.manager.brain.add_feedback(features, label)
            
            # Mise à jour du statut en base
            self.manager.conn.execute(
                "UPDATE inventory SET status=? WHERE hash=?", (action, file_hash)
            )
            self.manager.conn.commit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Instance du contrôleur
    controller = AppController()
    controller.view.show()
    
    sys.exit(app.exec())
