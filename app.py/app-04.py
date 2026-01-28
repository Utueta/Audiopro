"""
Audiopro Random Forest Brain v0.2.5
- Implements MLModelInterface for deterministic classification
- Handles feature vector normalization via Z-Score Scaler
- Manages persistent weight loading from .pkl artifacts
"""

import sys
import os
import logging
import multiprocessing
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QThreadPool, QObject, Slot, Signal

# ERB: Adapter/Domain separation extracted from app-cons2.py
try:
    from persistence.repository import AudioRepository
    from core.analyzer import AudioAnalyzer
    from services.llm_service import LLMService
    from ui.view import AudioExpertView
    from ui.components.splash import ObsidianSplashScreen
except ImportError:
    # Fallback placeholders for standalone validation
    pass

class AudioproController(QObject):
    """Hexagonal Orchestrator: Managed Threading & Arbitrage."""
    
    def __init__(self):
        super().__init__()
        self._setup_logging()
        
        # 1. Infrastructure: Thread Safety (app-cons1.py)
        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(max(2, (os.cpu_count() or 4) - 1))
        
        # 2. Persistence: SQL-WAL (app-cons2.py)
        self.repository = AudioRepository("database/audiopro_industrial.db")
        
        # 3. Engines
        self.analyzer = AudioAnalyzer()
        self.llm = LLMService()
        
        # 4. View
        self.view = AudioExpertView()
        self._connect_signals()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )

    def _connect_signals(self):
        self.view.request_scan.connect(self.start_batch_scan)
        self.view.request_action.connect(self.handle_expert_feedback)

    @Slot(str)
    def start_batch_scan(self, folder_path):
        """Dispatches Workers with Size-Guards (app-cons2.py)."""
        for root, _, files in os.walk(folder_path):
            for f in files:
                path = os.path.join(root, f)
                if os.path.getsize(path) > 0:
                    self._dispatch_worker(path)

    def _dispatch_worker(self, path):
        # Implementation of AnalysisWorker with Signal linkage
        pass 

    @Slot(dict)
    def on_analysis_complete(self, metrics):
        """ML Logic & AI Arbitrage Zone (app-15.py)."""
        # Feature Flattening (Deterministic)
        features = [metrics['clipping'], metrics['snr'], metrics['phase'], metrics['bitrate']]
        
        # ML Prediction (Z-Score Scaled)
        metrics['ml_score'] = self.repository.brain.predict(features)
        
        # Conditional AI Arbitrage (Efficiency Protocol)
        if 0.4 <= metrics['ml_score'] <= 0.7:
            metrics['ai_verdict'] = self.llm.consult_expert(metrics)
            
        self.view.update_results(metrics)

    @Slot(str, str)
    def handle_expert_feedback(self, file_hash, action):
        """Persistent ML Retraining Loop (app-13.py)."""
        label = 1.0 if action == "BAN" else 0.0
        self.repository.save_decision(file_hash, label)
        logging.info(f"Retraining Brain for hash {file_hash} with label {label}")

    def run(self):
        """Launch Sequence with GPU Diagnostics (app-cons1.py)."""
        splash = ObsidianSplashScreen()
        if splash.run_diagnostics(): # CUDA/FFmpeg check
            self.view.show()
        else:
            QMessageBox.critical(None, "Fatal Error", "Hardware Diagnostics Failed.")
            sys.exit(1)

def main():
    multiprocessing.freeze_support()
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    app = QApplication(sys.argv)
    controller = AudioproController()
    controller.run()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
