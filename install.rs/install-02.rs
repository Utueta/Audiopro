---
FILE:config.json
{
    "project_info": {"version": "0.2.4", "edition": "Obsidian Pro", "developer_mode": false},
    "paths": {
        "db_path": "database/audio_expert_v01.db",
        "model_path": "models/audio_expert_rf.joblib",
        "scaler_path": "models/scaler.pkl",
        "log_path": "logs/session.log"
    },
    "audio": {
        "sample_duration_sec": 45,
        "extensions": [".flac", ".wav", ".mp3", ".m4a", ".ogg", ".aac", ".wma"]
    },
    "ml_engine": {
        "initial_weights": {"clipping": 0.3, "snr": 0.2, "crackling": 0.3, "quality": 0.2}
    },
    "llm": {
        "model_name": "qwen2.5",
        "api_url": "http://localhost:11434/api/generate",
        "arbitration_zone": {"min_score": 0.4, "max_score": 0.75}
    }
}

---
FILE:app.py
import sys, multiprocessing
from PySide6.QtWidgets import QApplication
from core_logic import AudioExpertApp

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    core = AudioExpertApp()
    core.run()
    sys.exit(app.exec())

---
FILE:core_logic.py
import json, os
from PySide6.QtCore import QObject, QThreadPool
from ui.view import AudioExpertView
from analyzer import AudioAnalyzer
from model import FraudModel
from services.llm_service import LLMService
from workers import AnalysisWorker

class AudioExpertApp(QObject):
    def __init__(self):
        super().__init__()
        self.config = json.load(open("config.json"))
        self.analyzer = AudioAnalyzer(self.config)
        self.model = FraudModel(self.config)
        self.llm = LLMService(self.config)
        self.threadpool = QThreadPool()
        self.view = AudioExpertView(self.config)
        
        self.view.scan_requested.connect(self.dispatch_analysis)
        self.view.feedback_given.connect(self.model.update_feedback)

    def dispatch_analysis(self, path):
        worker = AnalysisWorker(path, self.analyzer, self.model, self.llm)
        worker.signals.dsp_ready.connect(self.view.handle_dsp_ready)
        worker.signals.result.connect(self.view.handle_analysis_result)
        self.threadpool.start(worker)

    def run(self):
        self.view.show()

---
FILE:analyzer.py
import os, hashlib, numpy as np, librosa

class AudioAnalyzer:
    def __init__(self, config):
        self.cfg = config['audio']

    def get_metrics(self, path):
        if os.path.getsize(path) == 0: return {"status": "defective", "reason": "0kb"}
        
        y, sr = librosa.load(path, sr=None, duration=self.cfg['sample_duration_sec'])
        h = hashlib.blake2b(open(path, "rb").read(), digest_size=16).hexdigest()
        
        # Clipping & Crackling
        clipping = np.sum(np.abs(y) >= 0.95) / len(y)
        crackling = np.sum(np.abs(np.diff(y)) > 0.4) / len(y)
        
        # SNR
        rms = librosa.feature.rms(y=y)[0]
        snr = 20 * np.log10(np.mean(rms) / (np.std(y) + 1e-6))
        
        # Score Qualité (0-100)
        quality = 100 * (1.0 - min(clipping * 5 + crackling * 50, 0.9))
        
        # Matrix pour Spectrogramme
        s_mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        matrix = librosa.power_to_db(s_mel, ref=np.max)

        return {
            "filename": os.path.basename(path), "hash": h, "matrix": matrix,
            "clipping": float(clipping), "snr": float(snr), "crackling": float(crackling),
            "quality_score": float(quality), "centroid": float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))),
            "status": "ok"
        }

---
FILE:ui/view.py
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QTextEdit, QSlider, QLabel
from PySide6.QtCore import Qt, Signal
from ui.components import SpectralWidget

class AudioExpertView(QMainWindow):
    scan_requested = Signal(str)
    feedback_given = Signal(str, str)

    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("AUDIO EXPERT PRO V0.2.4")
        self.resize(1100, 800)
        self.setAcceptDrops(True)
        self.current_hash = None
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("DÉPOSEZ UN FICHIER")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        
        # Inspection
        self.tab_spec = QWidget()
        spec_l = QVBoxLayout(self.tab_spec)
        self.spec_view = SpectralWidget()
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(5, 100); self.zoom.setValue(100)
        self.zoom.valueChanged.connect(self.spec_view.set_zoom)
        spec_l.addWidget(self.spec_view)
        spec_l.addWidget(self.zoom)
        self.tabs.addTab(self.tab_spec, "SPECTROGRAMME")

        # Rapport
        self.report = QTextEdit("Diagnostic...")
        self.tabs.addTab(self.report, "RAPPORT IA")
        layout.addWidget(self.tabs)

        # Verdicts
        v_layout = QHBoxLayout()
        self.btn_bon = QPushButton("BON ✅")
        self.btn_ban = QPushButton("DÉFECTUEUX ❌")
        self.btn_bon.clicked.connect(lambda: self._verdict("bon"))
        self.btn_ban.clicked.connect(lambda: self._verdict("ban"))
        v_layout.addWidget(self.btn_bon); v_layout.addWidget(self.btn_ban)
        layout.addLayout(v_layout)

    def handle_dsp_ready(self, res):
        self.current_hash = res['hash']
        self.status_label.setText(f"QUALITÉ : {res.get('quality_score', 0):.1f}%")
        if 'matrix' in res: self.spec_view.update_data(res['matrix'])

    def handle_analysis_result(self, res):
        self.report.setText(f"Score Suspicion: {res['score']:.2f}\n\n{res.get('analysis_text', '')}")

    def _verdict(self, tag):
        if self.current_hash: self.feedback_given.emit(self.current_hash, tag)

    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dropEvent(self, e):
        for url in e.mimeData().urls(): self.scan_requested.emit(url.toLocalFile())
