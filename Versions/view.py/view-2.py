import os
import sys
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QProgressBar, QLabel)
from PySide6.QtCore import Qt, Slot, Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class AudioExpertView(QMainWindow):
    # Signaux pour communiquer avec le contrôleur (app.py)
    request_scan = Signal(str)
    request_action = Signal(str, str) # hash, action (GOOD/BAN)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Expert Pro V2.0 - Obsidian Dark")
        self.resize(1200, 800)
        self._apply_theme()
        
        # Central Widget & Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Initialisation des onglets
        self.tab_scan = QWidget()
        self.tab_results = QWidget()
        self.tab_revision = QWidget()
        self.tab_duplicates = QWidget()
        
        self.tabs.addTab(self.tab_scan, "🚀 SCAN")
        self.tabs.addTab(self.tab_results, "📊 RÉSULTATS")
        self.tabs.addTab(self.tab_revision, "🔍 RÉVISION")
        self.tabs.addTab(self.tab_duplicates, "👯 DOUBLONS")
        
        self._setup_scan_tab()
        self._setup_results_tab()
        self._setup_revision_tab()

    def _apply_theme(self):
        """Design system 'Deep Obsidian Dark'."""
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; }
            QTabWidget::pane { border: 1px solid #333; background: #1a1a1a; }
            QTabBar::tab { background: #2d2d2d; color: #888; padding: 10px 20px; }
            QTabBar::tab:selected { background: #1a1a1a; color: #00f2ff; border-bottom: 2px solid #00f2ff; }
            QPushButton { background-color: #00f2ff; color: #000; font-weight: bold; border-radius: 4px; padding: 8px; }
            QPushButton:hover { background-color: #00c8d4; }
            QTableWidget { background-color: #262626; color: #eee; gridline-color: #333; }
        """)

    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        
        self.btn_select = QPushButton("SÉLECTIONNER UN DOSSIER À ANALYSER")
        self.btn_select.clicked.connect(self._open_folder_dialog)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00f2ff; }")
        
        self.log_output = QLabel("Prêt pour l'analyse...")
        self.log_output.setAlignment(Qt.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(self.btn_select)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output)
        layout.addStretch()

    def _setup_results_tab(self):
        layout = QVBoxLayout(self.tab_results)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Fichier", "Clipping", "SNR", "Suspicion", "Verdict"])
        layout.addWidget(self.results_table)

    def _setup_revision_tab(self):
        """L'onglet Expert avec Waveform & Spectrogramme."""
        layout = QHBoxLayout(self.tab_revision)
        
        # Côté gauche : Liste des fichiers en zone grise
        self.review_list = QTableWidget(0, 2)
        layout.addWidget(self.review_list, 1)
        
        # Côté droit : Visualisation & Contrôles
        viz_layout = QVBoxLayout()
        
        self.figure, (self.ax_wave, self.ax_spec) = plt.subplots(2, 1, figsize=(6, 8))
        self.figure.patch.set_facecolor('#1a1a1a')
        self.canvas = FigureCanvas(self.figure)
        
        viz_layout.addWidget(self.canvas)
        
        btn_layout = QHBoxLayout()
        self.btn_good = QPushButton("✓ MARQUER COMME BON")
        self.btn_good.setStyleSheet("background-color: #2ecc71; color: white;")
        self.btn_ban = QPushButton("✗ BANNIR (FAUX HQ / DÉFAUT)")
        self.btn_ban.setStyleSheet("background-color: #e74c3c; color: white;")
        
        btn_layout.addWidget(self.btn_good)
        btn_layout.addWidget(self.btn_ban)
        viz_layout.addLayout(btn_layout)
        
        layout.addLayout(viz_layout, 2)

    def _open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner Dossier")
        if folder:
            self.request_scan.emit(folder)

    @Slot(dict)
    def update_results(self, data):
        """Met à jour le tableau des résultats en temps réel."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(os.path.basename(data['path'])))
        self.results_table.setItem(row, 1, QTableWidgetItem(f"{data['dsp']['clipping']:.2f}%"))
        self.results_table.setItem(row, 2, QTableWidgetItem(f"{data['dsp']['snr']:.1f} dB"))
        
        score_item = QTableWidgetItem(f"{data['ml_score']:.2f}")
        # Coloration dynamique selon suspicion
        if data['ml_score'] > 0.7: score_item.setForeground(Qt.red)
        elif data['ml_score'] < 0.4: score_item.setForeground(Qt.green)
        
        self.results_table.setItem(row, 3, QTableWidgetItem(score_item))

    @Slot(object, object)
    def draw_visuals(self, times, waveform, spectrogram):
        """Affiche les graphiques sans bloquer l'UI."""
        self.ax_wave.clear()
        self.ax_spec.clear()
        
        self.ax_wave.plot(times, waveform, color='#00f2ff', linewidth=0.5)
        self.ax_wave.set_facecolor('#1a1a1a')
        self.ax_wave.axis('off')
        
        self.ax_spec.imshow(spectrogram, aspect='auto', origin='lower', cmap='inferno')
        self.ax_spec.axis('off')
        
        self.canvas.draw()
