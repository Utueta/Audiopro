 ---

FILE:config.json

{

    "project_info": {

        "version": "0.2.4",

        "edition": "Obsidian Pro",

        "developer_mode": false

    },

    "paths": {

        "db_path": "database/audio_expert_v01.db",

        "model_path": "models/audio_expert_rf.joblib",

        "scan_history": "database/history.json",

        "log_path": "logs/session.log",

        "assets_path": "assets/"

    },

    "audio": {

        "sample_duration_sec": 45,

        "extensions": [".flac", ".wav", ".alac", ".mp3", ".m4a"],

        "analysis_params": {

            "fake_hq_threshold_khz": 16.5,

            "clipping_sensitivity": 0.05,

            "snr_min_db": 20.0

        }

    },

    "ml_engine": {

        "auto_weight_adjust": true,

        "retrain_every": 5,

        "initial_weights": {

            "spectral_cut": 0.5,

            "clipping": 0.2,

            "snr": 0.2,

            "phase": 0.1

        }

    },

    "performance": {

        "max_threads": 4,

        "thread_priority": "HighPriority"

    },

    "llm": {

        "model_name": "qwen2.5",

        "api_url": "http://localhost:11434/api/generate",

        "arbitration_zone": {

            "min_score": 0.4,

            "max_score": 0.75

        }

    },

    "ui_settings": {

        "theme": "obsidian_dark",

        "colormap": "inferno",

        "enable_mini_player": true,

        "refresh_rate_ms": 100

    }

}

---

FILE:requirements.txt

PySide6>=6.6.1

librosa==0.10.1

numpy<2.0.0

scipy>=1.11.4

scikit-learn>=1.3.2

joblib>=1.3.2

requests>=2.31.0

mutagen>=1.47.0

---

FILE:app.py

import sys, os, json, logging

from PySide6.QtWidgets import QApplication, QMessageBox

from PySide6.QtCore import Qt, QThreadPool

from view import AudioExpertView

from splash_screen import SplashScreen

from analyzer import AudioAnalyzer

from model import FraudModel

from services.llm_service import LLMService

from workers import AnalysisWorker


class AudioExpertApp:

    def __init__(self):

        self.config_path = "config.json"

        self.config = self._load_config()

        self._setup_logging()

        self._init_fs()

        

        self.analyzer = AudioAnalyzer(self.config)

        self.model = FraudModel(self.config)

        self.llm = LLMService(self.config)

        

        self.threadpool = QThreadPool()

        self.threadpool.setMaxThreadCount(self.config.get('performance', {}).get('max_threads', 4))

        

        self.view = AudioExpertView(self.config)

        self._connect_signals()


    def _load_config(self):

        if not os.path.exists(self.config_path): sys.exit(1)

        with open(self.config_path, "r", encoding='utf-8') as f: return json.load(f)


    def _setup_logging(self):

        log_path = self.config['paths']['log_path']

        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


    def _init_fs(self):

        for p in ["database", "models", "logs", "assets", "services", "scripts"]:

            os.makedirs(p, exist_ok=True)


    def _connect_signals(self):

        self.view.scan_requested.connect(self.dispatch_worker)

        self.view.feedback_given.connect(self.model.update_feedback)


    def dispatch_worker(self, file_path):

        worker = AnalysisWorker(file_path, self.analyzer, self.model, self.llm)

        worker.signals.dsp_ready.connect(self.view.handle_dsp_ready)

        worker.signals.result.connect(self.on_analysis_finished)

        self.threadpool.start(worker)


    def on_analysis_finished(self, results):

        self.view.handle_analysis_result(results)

        self.model.save_analysis(results, results['score'])


    def run(self):

        splash = SplashScreen(self.config)

        if splash.run_checks():

            splash.close()

            self.view.show()

        else:

            QMessageBox.critical(None, "Erreur Système", "Intégrité système non conforme (Vérifiez Ollama).")

            sys.exit(1)


if __name__ == "__main__":

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)

    core = AudioExpertApp()

    core.run()

    sys.exit(app.exec())

---

FILE:view.py

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, QGraphicsDropShadowEffect, QTextEdit

from PySide6.QtCore import Qt, Signal, QPropertyAnimation

from PySide6.QtGui import QColor, QImage, QPixmap

import numpy as np


class AudioExpertView(QMainWindow):

    scan_requested = Signal(str)

    feedback_given = Signal(str, bool)


    def __init__(self, config):

        super().__init__()

        self.config, self.current_hash = config, None

        self.setAcceptDrops(True)

        self._setup_ui()


    def _setup_ui(self):

        self.setWindowTitle("AUDIO EXPERT PRO - OBSIDIAN V0.2.4")

        self.resize(1150, 800)

        self.central = QWidget()

        self.setCentralWidget(self.central)

        self.layout = QVBoxLayout(self.central)

        self.layout.setContentsMargins(20, 20, 20, 20)

        self.layout.setSpacing(15)


        # Status & Glow Effect

        self.status_label = QLabel("GLISSEZ UN FICHIER AUDIO")

        self.status_label.setAlignment(Qt.AlignCenter)

        self.status_label.setStyleSheet("font-size: 26px; color: #00F2FF; font-weight: bold; padding: 20px;")

        

        self.glow = QGraphicsDropShadowEffect()

        self.glow.setBlurRadius(0)

        self.glow.setColor(QColor(0, 242, 255))

        self.status_label.setGraphicsEffect(self.glow)

        self.layout.addWidget(self.status_label)


        # Expert Report Panel

        self.report_area = QTextEdit("IA : En attente d'analyse...")

        self.report_area.setReadOnly(True)

        self.report_area.setStyleSheet("background: #1A1C25; padding: 15px; border-radius: 8px; color: #BBBBBB; font-family: 'Consolas', monospace;")

        self.layout.addWidget(self.report_area)


        # Control UI

        self.layout.addWidget(QLabel("INSPECTION SPECTRALE (ZOOM)"))

        self.zoom_slider = QSlider(Qt.Horizontal)

        self.zoom_slider.setRange(5, 100)

        self.zoom_slider.setValue(100)

        self.layout.addWidget(self.zoom_slider)


        btns = QHBoxLayout()

        self.btn_ok = QPushButton("VERDICT CORRECT ✅")

        self.btn_ko = QPushButton("ERREUR IA ❌")

        for b in [self.btn_ok, self.btn_ko]:

            b.setFixedHeight(45)

            b.setStyleSheet("font-weight: bold; background: #2D3139; color: white; border-radius: 4px;")

        

        self.btn_ok.clicked.connect(lambda: self.submit_feedback(True))

        self.btn_ko.clicked.connect(lambda: self.submit_feedback(False))

        btns.addWidget(self.btn_ok)

        btns.addWidget(self.btn_ko)

        self.layout.addLayout(btns)


    def handle_dsp_ready(self, res):

        self.current_hash = res['hash']

        self.status_label.setText(f"SCORE DÉTECTÉ : {res['score']:.2f}")

        self._trigger_glow(res['score'] > 0.6)


    def handle_analysis_result(self, res):

        analysis = res.get('analysis_text', "")

        self.report_area.setText(f"RAPPORT D'EXPERTISE :\n\n{analysis if analysis else 'Analyse DSP pure complétée.'}")


    def submit_feedback(self, val):

        if self.current_hash:

            self.feedback_given.emit(self.current_hash, val)

            self.status_label.setText("FEEDBACK ENREGISTRÉ")


    def _trigger_glow(self, active):

        if hasattr(self, 'anim'): self.anim.stop()

        self.anim = QPropertyAnimation(self.glow, b"blurRadius")

        self.anim.setEndValue(30 if active else 0)

        self.anim.setDuration(1000)

        self.anim.start()


    def dragEnterEvent(self, e):

        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):

        for url in e.mimeData().urls(): self.scan_requested.emit(url.toLocalFile())

---

FILE:analyzer.py

import os, hashlib, numpy as np, librosa


class AudioAnalyzer:

    def __init__(self, config):

        self.cfg = config['audio']

        self.params = self.cfg['analysis_params']


    def get_metrics(self, file_path):

        # Hashage Blake2b (Identité unique)

        h = hashlib.blake2b(digest_size=16)

        with open(file_path, "rb") as f:

            while chunk := f.read(8192): h.update(chunk)

        

        # Moteur DSP (Physique du son)

        y, sr = librosa.load(file_path, sr=None, duration=self.cfg['sample_duration_sec'])

        s_mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)

        matrix = librosa.power_to_db(s_mel, ref=np.max)

        

        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

        clipping = np.sum(np.abs(y) >= (1.0 - self.params['clipping_sensitivity'])) / len(y)

        

        return {

            "filename": os.path.basename(file_path),

            "hash": h.hexdigest(),

            "matrix": matrix,

            "is_fake_hq": centroid < (self.params['fake_hq_threshold_khz'] * 1000),

            "clipping": float(clipping)

        }

---

FILE:model.py

import os, sqlite3, joblib

from PySide6.QtCore import QMutex, QMutexLocker


class FraudModel:

    def __init__(self, config):

        self.cfg = config['ml_engine']

        self.db_path = config['paths']['db_path']

        self.lock = QMutex()

        self._init_db()


    def _init_db(self):

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:

            conn.execute("CREATE TABLE IF NOT EXISTS scans (hash TEXT PRIMARY KEY, score REAL, user_val INTEGER)")


    def predict(self, metrics):

        w = self.cfg['initial_weights']

        # Algorithme hybride : Physique + ML ready

        score = (0.85 if metrics['is_fake_hq'] else 0.1) * w['spectral_cut']

        score += metrics['clipping'] * w['clipping']

        return min(float(score), 1.0)


    def save_analysis(self, metrics, score):

        with QMutexLocker(self.lock):

            with sqlite3.connect(self.db_path) as conn:

                conn.execute("INSERT OR REPLACE INTO scans (hash, score) VALUES (?, ?)", (metrics['hash'], score))


    def update_feedback(self, f_hash, val):

        with QMutexLocker(self.lock):

            with sqlite3.connect(self.db_path) as conn:

                conn.execute("UPDATE scans SET user_val = ? WHERE hash = ?", (1 if val else 0, f_hash))

---

FILE:workers.py

import traceback

from PySide6.QtCore import QRunnable, QObject, Signal, Slot


class AnalysisSignals(QObject):

    dsp_ready = Signal(dict)

    result = Signal(dict)

    error = Signal(tuple)


class AnalysisWorker(QRunnable):

    def __init__(self, file_path, analyzer, model, llm=None):

        super().__init__()

        self.file_path, self.analyzer, self.model, self.llm = file_path, analyzer, model, llm

        self.signals = AnalysisSignals()


    @Slot()

    def run(self):

        try:

            # Phase 1: Physique (Instant)

            metrics = self.analyzer.get_metrics(self.file_path)

            metrics['score'] = self.model.predict(metrics)

            self.signals.dsp_ready.emit(metrics)

            

            # Phase 2: Arbitrage IA (Si zone grise)

            metrics['analysis_text'] = ""

            if self.llm and self.llm.check_arbitration(metrics['score']):

                metrics['analysis_text'] = self.llm.analyze_anomaly(metrics)

            

            self.signals.result.emit(metrics)

        except Exception as e:

            self.signals.error.emit((e, traceback.format_exc()))

---

FILE:services/llm_service.py

import requests


class LLMService:

    def __init__(self, config):

        self.cfg = config['llm']


    def check_arbitration(self, score):

        z = self.cfg['arbitration_zone']

        return z['min_score'] <= score <= z['max_score']


    def analyze_anomaly(self, metrics):

        try:

            res = requests.post(self.cfg['api_url'], json={

                "model": self.cfg['model_name'],

                "prompt": f"Audit audio expert : {metrics['filename']}. Score de suspicion {metrics['score']:.2f}. Clipping {metrics['clipping']:.4f}. Rédige un diagnostic court.",

                "stream": False

            }, timeout=15)

            return res.json().get('response', "IA occupée.")

        except: return "Ollama déconnecté."

---

FILE:splash_screen.py

import requests

from PySide6.QtWidgets import QSplashScreen

from PySide6.QtCore import Qt

from PySide6.QtGui import QPixmap, QColor


class SplashScreen(QSplashScreen):

    def __init__(self, config):

        pixmap = QPixmap(500, 250)

        pixmap.fill(QColor("#0F111A"))

        super().__init__(pixmap)

        self.config = config


    def run_checks(self):

        self.showMessage("CONTRÔLE INTÉGRITÉ IA...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)

        try:

            requests.get(self.config['llm']['api_url'].replace('/generate', '/tags'), timeout=2)

            return True

        except: return False

---

FILE:init_model.py

import joblib, os, numpy as np

from sklearn.ensemble import RandomForestClassifier


def init():

    path = "models/audio_expert_rf.joblib"

    os.makedirs(os.path.dirname(path), exist_ok=True)

    X = np.array([[18000, 0.0], [12000, 0.1], [20000, 0.0], [9000, 0.5]])

    y = np.array([0, 1, 0, 1])

    clf = RandomForestClassifier(n_estimators=10).fit(X, y)

    joblib.dump(clf, path)

    print(f"✅ Modèle amorcé : {path}")


if __name__ == "__main__": init()

---

FILE:scripts/reset_brain.sh

#!/bin/bash

echo "⚠️ Purge de la mémoire applicative (Database/Models)..."

rm -rf ../database/*

rm -rf ../models/*.joblib

rm -rf ../logs/*.log

echo "✅ Système prêt pour un nouvel entraînement."

---

FILE:scripts/check_health.py

import sys, os, requests


def check():

    print("📋 Diagnostic Audio Expert Pro V0.2.4")

    # Check Ollama

    try:

        requests.get("http://localhost:11434/api/tags", timeout=1)

        print("✅ Ollama : CONNECTÉ")

    except:

        print("❌ Ollama : HORS-LIGNE")

    

    # Check Venv

    if sys.base_prefix != sys.prefix:

        print("✅ Environnement Virtuel : OK")

    else:

        print("⚠️ Attention : Non exécuté dans un Venv")


if __name__ == "__main__": check()

--- 
