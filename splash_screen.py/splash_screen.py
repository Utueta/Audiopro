#"""
# Audiopro v0.3.1
# - Handles boot diagnostics gatekeeping (Ollama, GPU presence, CPU/RAM health).
#"""

from __future__ import annotations

import os
import sys

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from scripts.check_health import check_system


class AudioproSplashScreen(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(600, 300)
        pixmap.fill(Qt.black)
        super().__init__(pixmap)
        self.showMessage("Audiopro v0.3.1 — Pre-flight diagnostics...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)

    def run_diagnostics(self) -> bool:
        """Verifies system integrity before UI handoff.

        Required behaviors:
          - Detect CUDA/GPU absence and set CPU fallback for LLM inference.
          - CPU/RAM availability warnings (non-blocking unless critical).
        """
        self.showMessage("CHECKING INFRASTRUCTURE (OLLAMA/CUDA)...", Qt.AlignBottom | Qt.AlignCenter, Qt.cyan)
        QApplication.processEvents()

        health = check_system()

        if not health.get("ollama", False):
            self.showMessage("CRITICAL ERROR: OLLAMA OFFLINE", Qt.AlignBottom | Qt.AlignCenter, Qt.red)
            return False

        # GPU absence detection (graceful degradation)
        if not health.get("gpu", False):
            # Signal to composition root / services: force CPU-based inference (if supported)
            os.environ["AUDIOPRO_LLM_DEVICE"] = "cpu"
            self.showMessage("WARNING: GPU NOT DETECTED — FALLING BACK TO CPU LLM", Qt.AlignBottom | Qt.AlignCenter, Qt.yellow)
            QApplication.processEvents()
        else:
            os.environ.pop("AUDIOPRO_LLM_DEVICE", None)

        # CPU/RAM fallback guardrails (warn; do not block launch unless critically low)
        vm = psutil.virtual_memory()
        if vm.available < (512 * 1024 * 1024):  # <512MB free is operationally unsafe
            self.showMessage("CRITICAL ERROR: INSUFFICIENT RAM", Qt.AlignBottom | Qt.AlignCenter, Qt.red)
            return False
        if (vm.percent >= 85.0):
            self.showMessage("WARNING: HIGH RAM UTILIZATION (>=85%)", Qt.AlignBottom | Qt.AlignCenter, Qt.yellow)
            QApplication.processEvents()

        self.showMessage("SYSTEM READY. LAUNCHING DASHBOARD...", Qt.AlignBottom | Qt.AlignCenter, Qt.green)
        return True
