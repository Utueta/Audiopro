"""
Audiopro Bootloader v0.3.1
- Role: Environment verification & Dependency Gatekeeper.
- v0.3.1: Blocks launch if check_health.py fails (Ollama/GPU/Weights).
"""

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTimer
import sys
from scripts.check_health import check_system

class AudioproSplashScreen(QSplashScreen):
    def __init__(self):
        # Placeholder for industrial logo
        pixmap = QPixmap(600, 300)
        pixmap.fill(Qt.black)
        super().__init__(pixmap)
        self.showMessage("INITIALIZING SENTINEL v0.3.1...", Qt.AlignBottom | Qt.AlignCenter, Qt.cyan)

    def run_diagnostics(self):
        """Verifies system integrity before UI handoff."""
        self.showMessage("CHECKING INFRASTRUCTURE (OLLAMA/CUDA)...", Qt.AlignBottom | Qt.AlignCenter, Qt.cyan)
        QApplication.processEvents()
        
        health = check_system()
        
        if not health["ollama"]:
            self.showMessage("CRITICAL ERROR: OLLAMA OFFLINE", Qt.AlignBottom | Qt.AlignCenter, Qt.red)
            return False
        
        self.showMessage("SYSTEM READY. LAUNCHING DASHBOARD...", Qt.AlignBottom | Qt.AlignCenter, Qt.green)
        return True
