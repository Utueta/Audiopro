"""
Audiopro v0.3.1
Handles the global Application Constructor, Dependency Injection, and Signal Routing.
"""
import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from core.manager import SystemManager
from core.brain.random_forest import AudioBrain
from persistence.repository import Repository
from ui.view import AudioproDashboard 

# Industrial Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("system.init")

class AudioproApp:
    """
    Audiopro Entry Point v0.3.1
    - Initializes DB -> ML Brain (with Scaler) -> Manager -> UI.
    - Merged: Standardized database path to database/audiopro_v03.db.
    """
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        
        # 1. Initialize Components (Industrial v0.3.1 Signature Merge)
        # Brain now requires explicit model and scaler paths for Z-Score normalization
        self.repository = Repository("database/audiopro_v03.db")
        self.brain = AudioBrain(
            model_path="core/brain/weights/random_forest.pkl",
            scaler_path="core/brain/weights/scaler_v0.3.pkl"
        )
        self.manager = SystemManager(self.repository, self.brain)
        
        # 2. Initialize UI (v0.3.1 Obsidian Pro Edition)
        self.window = AudioproDashboard(self.manager)
        
        # 3. Wire Up Feedback and Update Signals
        self._setup_connections()
        
        logger.info("Audiopro Suite v0.3.1: Initialization Complete.")

    def _setup_connections(self):
        """Connects UI actions to Manager logic."""
        # Signal: Human correction from UI -> DB (Ground Truth)
        self.window.human_verdict_submitted.connect(
            self.manager.register_human_correction
        )
        
        # Signal: Refresh Brain request from UI -> Hot Reload
        self.window.refresh_brain_requested.connect(self._handle_brain_refresh)

    def _handle_brain_refresh(self):
        """Triggers the manager to reload weights and notifies the user."""
        success = self.manager.refresh_brain()
        if success:
            QMessageBox.information(self.window, "Brain Update", "Model weights and Scalers successfully updated!")
        else:
            QMessageBox.critical(self.window, "Update Failed", "Could not reload brain artifacts. Check logs.")

    def run(self):
        self.window.show()
        sys.exit(self.qapp.exec())

if __name__ == "__main__":
    app = AudioproApp()
    app.run()
