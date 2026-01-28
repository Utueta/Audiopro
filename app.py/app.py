"""
Audiopro Entry Point v0.3.1
- Role: Global Application Constructor and Signal Router.
- Logic: Initializes DB -> ML Brain -> Manager -> UI.
- Merged: Standardized database path to database/audiopro_v03.db.
"""

import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from core.manager import AuditManager
from core.brain.random_forest import AudioBrain
from persistence.repository import AuditRepository
from ui.view import AudioproDashboard 

# Industrial Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("system.init")

class AudioproApp:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        
        # 1. Initialize Components (Standardized Path Merge)
        self.repository = AuditRepository("database/audiopro_v03.db")
        self.brain = AudioBrain("core/brain/weights")
        self.manager = AuditManager(self.repository, self.brain)
        
        # 2. Initialize UI
        self.window = AudioproDashboard(self.manager)
        
        # 3. Wire Up Feedback and Update Signals
        self._setup_connections()
        
        logger.info("Audiopro Suite v0.3.1: Initialization Complete.")

    def _setup_connections(self):
        """Connects UI actions to Manager logic."""
        # Signal: Human correction from UI -> DB
        self.window.human_verdict_submitted.connect(
            self.manager.register_human_correction
        )
        
        # Signal: Refresh Brain request from UI -> Hot Reload
        self.window.refresh_brain_requested.connect(self._handle_brain_refresh)

    def _handle_brain_refresh(self):
        """Triggers the manager to reload weights and notifies the user."""
        success = self.manager.refresh_brain()
        if success:
            QMessageBox.information(self.window, "Brain Update", "Model weights successfully updated!")
        else:
            QMessageBox.critical(self.window, "Update Failed", "Could not reload brain weights. Check logs.")

    def run(self):
        self.window.show()
        sys.exit(self.qapp.exec())

if __name__ == "__main__":
    app = AudioproApp()
    app.run()
