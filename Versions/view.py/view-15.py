from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import librosa.display
import numpy as np

class MainView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Expert Pro V4.1 - Ultra Edition")
        self.setMinimumSize(1300, 900)
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Initialisation des 3 onglets
        self.tab_scan = QWidget()
        self.tab_review = QWidget()
        self.tab_duplicates = QWidget()
        
        self.tabs.addTab(self.tab_scan, "🚀 Scan Pipeline")
        self.tabs.addTab(self.tab_review, "🎧 Visualisation & Player")
        self.tabs.addTab(self.tab_duplicates, "👯 Doublons")

        self._setup_scan_tab()
        self._setup_review_tab()
        self._setup_duplicates_tab()

    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        
        # Barre d'outils Scan
        top_bar = QHBoxLayout()
        self.btn_start = QPushButton("📁 Sélectionner & Scanner Dossier")
        self.btn_start.setStyleSheet("padding: 10px; font-weight: bold; background-color: #2ecc71; color: white;")
        
        self.combo_options = QComboBox()
        self.combo_options.addItems(["Scan Rapide", "Scan Profond", "Ré-analyser tout"])
        
        top_bar.addWidget(self.btn_start, 3)
        top_bar.addWidget(self.combo_options, 1)
        
        # Tableau Principal
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Fichier", "Score ML", "Status", "Verdict LLM"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Journal de log
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        self.log.setStyleSheet("background-color: #2c3e50; color: #ecf0f1; font-family: monospace;")
        
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("📜 Journal d'analyse :"))
        layout.addWidget(self.log)

    def _setup_review_tab(self):
        layout = QHBoxLayout(self.tab_review)
        
        # --- CÔTÉ GAUCHE : VISUALISATION ---
        left_side = QVBoxLayout()
        
        # Création des deux graphiques (Waveform + Spectrogramme)
        
        self.fig, (self.ax_wave, self.ax_spec) = plt.subplots(2, 1, figsize=(8, 10))
        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvas(self.fig)
        
        left_side.addWidget(self.canvas)
        
        # --- CÔTÉ DROIT : CONTRÔLES ---
        right_side = QVBoxLayout()
        
        self.info_box = QGroupBox("🔍 Détails de l'analyse")
        info_layout = QVBoxLayout()
        self.lbl_details = QLabel("Sélectionnez un fichier pour voir les détails...")
        self.lbl_details.setWordWrap(True)
        info_layout.addWidget(self.lbl_details)
        self.info_box.setLayout(info_layout)
        
        # Boutons de décision
        self.btn_good = QPushButton("✅ VALIDER (Bon)")
        self.btn_good.setStyleSheet("background-color: #27ae60; color: white; height: 40px; font-weight: bold;")
        
        self.btn_bad = QPushButton("❌ REJETER (Ban)")
        self.btn_bad.setStyleSheet("background-color: #c0392b; color: white; height: 40px; font-weight: bold;")
        
        right_side.addWidget(self.info_box)
        right_side.addStretch()
        right_side.addWidget(self.btn_good)
        right_side.addWidget(self.btn_bad)
        
        layout.addLayout(left_side, 3)
        layout.addLayout(right_side, 1)

    def _setup_duplicates_tab(self):
        layout = QVBoxLayout(self.tab_duplicates)
        
        self.table_dup = QTableWidget(0, 3)
        self.table_dup.setHorizontalHeaderLabels(["Doublon (inférieur)", "Raison", "Original (conservé)"])
        self.table_dup.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.btn_clean_duplicates = QPushButton("🗑️ Marquer les doublons pour suppression")
        self.btn_clean_duplicates.setStyleSheet("background-color: #e67e22; color: white; padding: 10px;")
        
        layout.addWidget(QLabel("👯 Doublons identifiés par Hash & Bitrate :"))
        layout.addWidget(self.table_dup)
        layout.addWidget(self.btn_clean_duplicates)

    def update_visuals(self, path, ts_sample):
        """Mise à jour synchronisée Waveform + Spectrogramme."""
        try:
            # Charger 30 secondes pour la visualisation
            y, sr = librosa.load(path, duration=30)
            
            # 1. Waveform
            self.ax_wave.clear()
            librosa.display.waveshow(y, sr=sr, ax=self.ax_wave, color='#3498db')
            if ts_sample > 0:
                self.ax_wave.axvline(x=ts_sample, color='red', linestyle='--', label='Défaut détecté')
            self.ax_wave.set_title(f"Waveform : {os.path.basename(path)}")
            
            # 2. Spectrogramme (La clé pour le Fake HQ)
            self.ax_spec.clear()
            S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
            S_db = librosa.power_to_db(S, ref=np.max)
            img = librosa.display.specshow(S_db, x_axis='time', y_axis='mel', sr=sr, ax=self.ax_spec)
            self.ax_spec.set_title("Analyse Spectrale (Vérification 16kHz+)")
            
            self.canvas.draw()
        except Exception as e:
            print(f"Erreur d'affichage : {e}")

import os
