import os
import sys
import numpy as np
import pynvml 
import librosa
import librosa.display

# --- OPTIMISATION 1 : Backend QtAgg ---
import matplotlib
matplotlib.use('QtAgg') 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QLabel, QProgressBar, QFileDialog, QHeaderView)
from PySide6.QtCore import Qt, QTimer, Signal

class AudioExpertView(QMainWindow):
    scan_requested = Signal(str)
    label_submitted = Signal(str, str) # Hash, Label

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle(f"Audio Expert Pro V{self.config['project']['version']}")
        self.resize(1280, 850)
        
        # État interne pour la visualisation
        self.current_selected_path = None
        
        # Initialisation NVML
        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.has_gpu = True
        except:
            self.has_gpu = False

        self._init_ui()
        
        # Timer de monitoring (UI Refresh Rate)
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._update_gpu_stats)
        self.monitor_timer.start(self.config['ui_settings']['refresh_rate_ms'])

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # TOP BAR
        top_layout = QHBoxLayout()
        self.btn_scan = QPushButton("📁 SCANNER DOSSIER")
        self.btn_scan.setStyleSheet("font-weight: bold; padding: 10px;")
        self.btn_scan.clicked.connect(self._on_scan_clicked)
        
        self.gpu_label = QLabel("GPU: --% | VRAM: --/-- MB")
        self.gpu_bar = QProgressBar()
        self.gpu_bar.setFixedWidth(150)

        top_layout.addWidget(self.btn_scan)
        top_layout.addStretch()
        top_layout.addWidget(self.gpu_label)
        top_layout.addWidget(self.gpu_bar)
        main_layout.addLayout(top_layout)

        # TABLE
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Fichier", "Bitrate", "Score ML", "Fake HQ", "Arbitrage LLM", "Verdict", "Hash"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        main_layout.addWidget(self.table)

        # --- SECTION VISUALISATION ---
        viz_container = QWidget()
        viz_layout = QHBoxLayout(viz_container)
        self.figure, (self.ax_wave, self.ax_spec) = plt.subplots(1, 2, figsize=(12, 4))
        self.figure.patch.set_facecolor('#f0f0f0')
        self.canvas = FigureCanvas(self.figure)
        viz_layout.addWidget(self.canvas)
        main_layout.addWidget(viz_container)

    # --- OPTIMISATION 2 : Mise à jour via Signal (Thread-Safe) ---
    def process_new_analysis(self, metrics):
        """Appelé par app.py via le signal AnalysisWorker.result"""
        self.add_result_to_table(metrics)
        # On pourrait ici forcer l'affichage si c'est le premier résultat
        if self.table.rowCount() == 1:
            self.table.selectRow(0)

    def add_result_to_table(self, m):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Remplissage des cellules
        self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(m['path'])))
        self.table.setItem(row, 1, QTableWidgetItem(f"{m['meta']['bitrate']}k"))
        
        ml_item = QTableWidgetItem(f"{m['ml_score']:.2f}")
        self.table.setItem(row, 2, ml_item)
        
        hq_txt = "⚠️ FAKE" if m['is_fake_hq'] > 0.5 else "OK"
        hq_item = QTableWidgetItem(hq_txt)
        if m['is_fake_hq'] > 0.5: hq_item.setForeground(Qt.red)
        self.table.setItem(row, 3, hq_item)
        
        self.table.setItem(row, 4, QTableWidgetItem(m.get('llm_decision', 'AUTO')))
        
        # Feedback Buttons (Renforcement ML)
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(2, 2, 2, 2)
        
        btn_ban = QPushButton("BAN")
        btn_ban.setStyleSheet("background-color: #e74c3c; color: white; font-size: 10px;")
        btn_ban.clicked.connect(lambda: self.label_submitted.emit(m['hash'], "Ban"))
        
        btn_ok = QPushButton("GOOD")
        btn_ok.setStyleSheet("background-color: #2ecc71; color: white; font-size: 10px;")
        btn_ok.clicked.connect(lambda: self.label_submitted.emit(m['hash'], "Good"))
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_ban)
        self.table.setCellWidget(row, 5, btn_widget)
        
        # Cache pour le path (utilisé par la sélection)
        hash_item = QTableWidgetItem(m['hash'])
        hash_item.setData(Qt.UserRole, m['path']) 
        self.table.setItem(row, 6, hash_item)

    # --- OPTIMISATION 3 : Spectrogramme Rapide ---
    def update_plots(self, file_path):
        """Diagnostic visuel optimisé pour la fluidité de l'UI."""
        try:
            # Charge 5s après un offset de 10s (pour éviter les silences de début)
            y, sr = librosa.load(file_path, duration=5, offset=10)
            
            self.ax_wave.clear()
            self.ax_spec.clear()
            
            # Waveform
            self.ax_wave.plot(y, color='#3498db', alpha=0.7)
            self.ax_wave.set_title("Waveform (Clipping Check)")
            self.ax_wave.grid(True, alpha=0.3)
            
            # Spectrogramme léger (n_fft réduit)
            S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=1024, hop_length=512)
            S_db = librosa.power_to_db(S, ref=np.max)
            librosa.display.specshow(S_db, x_axis='time', y_axis='mel', sr=sr, ax=self.ax_spec)
            self.ax_spec.set_title("Spectro (Fake HQ Check)")
            
            self.canvas.draw_idle() 
        except Exception as e:
            print(f"Erreur Viz: {e}")

    def _on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            path = self.table.item(row, 6).data(Qt.UserRole)
            if path != self.current_selected_path:
                self.current_selected_path = path
                self.update_plots(path)

    def _update_gpu_stats(self):
        if self.has_gpu and self.config['ui_settings']['gpu_monitoring']:
            util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            used_mb = mem.used // 1024**2
            total_mb = mem.total // 1024**2
            self.gpu_label.setText(f"GPU: {util.gpu}% | VRAM: {used_mb}/{total_mb} MB")
            self.gpu_bar.setValue(util.gpu)

    def _on_scan_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier Musique")
        if folder:
            self.scan_requested.emit(folder)
