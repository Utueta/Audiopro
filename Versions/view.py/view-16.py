import os
import subprocess
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import librosa.display
import numpy as np

class MainView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Audio Expert Pro V5.0 - Nvidia Enhanced")
        self.setMinimumSize(1300, 900)
        
        # --- UI STRUCTURE ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab_scan = QWidget(); self.tab_review = QWidget(); self.tab_duplicates = QWidget()
        self.tabs.addTab(self.tab_scan, "🚀 Scan"); self.tabs.addTab(self.tab_review, "🎧 Révision"); self.tabs.addTab(self.tab_duplicates, "👯 Doublons")

        self._setup_scan_tab()
        self._setup_review_tab()
        self._setup_duplicates_tab()
        self._setup_gpu_monitor() # Nouvelle fonction V5.0

    def _setup_gpu_monitor(self):
        """Initialise les VU-mètres VRAM en bas de fenêtre"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.gpu_label = QLabel("GPU: --% | VRAM: --/-- MB")
        self.gpu_label.setStyleSheet("font-family: monospace; font-weight: bold; color: #3498db; padding-right: 20px;")
        self.status_bar.addPermanentWidget(self.gpu_label)
        
        # Timer de rafraîchissement (1 seconde)
        self.gpu_timer = QTimer()
        self.gpu_timer.timeout.connect(self._update_gpu_stats)
        self.gpu_timer.start(1000)

    def _update_gpu_stats(self):
        """Récupère les infos via nvidia-smi"""
        try:
            cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, shell=True).decode().strip().split(',')
            util, used, total = output[0], output[1], output[2]
            self.gpu_label.setText(f"GPU: {util}% | VRAM: {used}/{total} MB")
        except:
            self.gpu_label.setText("GPU: N/A (Nvidia-SMI non trouvé)")

    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        top = QHBoxLayout()
        self.btn_start = QPushButton("📁 Scanner Dossier")
        self.combo_options = QComboBox()
        self.combo_options.addItems(["Scan Rapide", "Scan Profond", "TOUS + Refresh"])
        top.addWidget(self.btn_start, 3); top.addWidget(self.combo_options, 1)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Fichier", "Score ML", "Status", "Verdict LLM"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(100)
        layout.addLayout(top); layout.addWidget(self.table); layout.addWidget(self.log)

    def _setup_review_tab(self):
        layout = QHBoxLayout(self.tab_review)
        left = QVBoxLayout()
        self.fig, (self.ax_wave, self.ax_spec) = plt.subplots(2, 1, figsize=(8, 10))
        self.canvas = FigureCanvas(self.fig)
        left.addWidget(self.canvas)
        
        right = QVBoxLayout()
        self.lbl_details = QLabel("Sélectionnez un fichier...")
        self.btn_good = QPushButton("✅ BON"); self.btn_bad = QPushButton("❌ BAN")
        right.addWidget(self.lbl_details); right.addStretch(); right.addWidget(self.btn_good); right.addWidget(self.btn_bad)
        layout.addLayout(left, 3); layout.addLayout(right, 1)

    def _setup_duplicates_tab(self):
        layout = QVBoxLayout(self.tab_duplicates)
        self.table_dup = QTableWidget(0, 3)
        self.table_dup.setHorizontalHeaderLabels(["Doublon", "Raison", "Original"])
        self.btn_clean_duplicates = QPushButton("🗑️ Nettoyer")
        layout.addWidget(self.table_dup); layout.addWidget(self.btn_clean_duplicates)

    def update_visuals(self, path, ts):
        try:
            y, sr = librosa.load(path, duration=30)
            self.ax_wave.clear(); librosa.display.waveshow(y, sr=sr, ax=self.ax_wave)
            self.ax_spec.clear(); S = librosa.feature.melspectrogram(y=y, sr=sr)
            librosa.display.specshow(librosa.power_to_db(S, ref=np.max), ax=self.ax_spec)
            self.canvas.draw()
        except: pass
