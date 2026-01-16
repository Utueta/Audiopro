import sys
import os
import numpy as np
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame, QProgressBar)
from PySide6.QtGui import QImage, QPixmap, QColor, QLinearGradient, QPalette, QBrush
from PySide6.QtCore import Qt, Signal, Slot, QSize

class AudioExpertView(QMainWindow):
    scan_requested = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ui_cfg = config['ui_settings']
        
        self.setWindowTitle(f"Audio Expert Pro - {config['project_info']['edition']}")
        self.setMinimumSize(1100, 750)
        self.is_mini_mode = False
        
        self._setup_styles()
        self._init_ui()

    def _setup_styles(self):
        """Applique la charte graphique Obsidian Pro."""
        self.setStyleSheet("""
            QMainWindow { background-color: #0F111A; }
            QWidget { color: #E0E0E0; font-family: 'Segoe UI', sans-serif; }
            
            QFrame#ControlPanel { 
                background-color: #161925; 
                border-radius: 12px; 
                border: 1px solid #1E2233;
            }
            
            QPushButton {
                background-color: #1E2233;
                border: 1px solid #00F2FF;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #00F2FF; color: #0F111A; }
            
            QTableWidget {
                background-color: #161925;
                border: none;
                gridline-color: #1E2233;
                selection-background-color: #1E2233;
            }
            QHeaderView::section {
                background-color: #0F111A;
                color: #00F2FF;
                padding: 5px;
                border: 1px solid #1E2233;
            }
            QProgressBar {
                border: 1px solid #1E2233;
                border-radius: 5px;
                text-align: center;
                background-color: #0F111A;
            }
            QProgressBar::chunk { background-color: #00F2FF; }
        """)

    def _init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        self.title_label = QLabel("AUDIO EXPERT PRO V0.2")
        self.title_label.setStyleSheet("font-size: 24px; color: #00F2FF; font-weight: bold;")
        
        self.btn_mini = QPushButton("MINI-MODE")
        self.btn_mini.setFixedSize(120, 35)
        self.btn_mini.clicked.connect(self.toggle_mini_mode)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_mini)
        self.main_layout.addLayout(header_layout)

        # --- Spectrogram Display (Rendu Natif) ---
        self.spec_label = QLabel("Prêt pour analyse...")
        self.spec_label.setAlignment(Qt.AlignCenter)
        self.spec_label.setFixedSize(1000, 350)
        self.spec_label.setStyleSheet("background-color: #050608; border-radius: 10px; border: 1px solid #1E2233;")
        self.main_layout.addWidget(self.spec_label, alignment=Qt.AlignCenter)

        # --- Results Table ---
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["Fichier", "Score ML", "Verdict", "Détails"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_layout.addWidget(self.results_table)

        # --- Footer Stats ---
        self.status_bar = QHBoxLayout()
        self.vram_label = QLabel("VRAM: --")
        self.cpu_label = QLabel("CPU: --")
        self.status_bar.addWidget(self.vram_label)
        self.status_bar.addWidget(self.cpu_label)
        self.main_layout.addLayout(self.status_bar)

    @Slot(np.ndarray)
    def update_spectrogram(self, S_db):
        """Génération Pixel-Perfect du spectrogramme Inferno sans Matplotlib."""
        # Normalisation entre 0 et 1
        S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min())
        h, w = S_norm.shape
        
        # Création de l'image (Format RGB32 pour la rapidité)
        img = QImage(w, h, QImage.Format_RGB32)
        
        for y in range(h):
            for x in range(w):
                val = S_norm[y, x]
                # Palette Inferno simplifiée : Noir -> Violet -> Orange -> Jaune
                r = int(min(255, val * 255 * 1.5))
                g = int(min(255, val**2 * 255))
                b = int(min(255, val**4 * 255))
                img.setPixel(x, h - 1 - y, QColor(r, g, b).rgb())

        pixmap = QPixmap.fromImage(img).scaled(self.spec_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.spec_label.setPixmap(pixmap)

    def toggle_mini_mode(self):
        """Bascule entre l'UI complète et le widget flottant."""
        if not self.is_mini_mode:
            self.setFixedSize(400, 150)
            self.results_table.hide()
            self.spec_label.hide()
            self.title_label.setText("AE Pro Mini")
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setMinimumSize(1100, 750)
            self.setFixedSize(1100, 750)
            self.results_table.show()
            self.spec_label.show()
            self.title_label.setText("AUDIO EXPERT PRO V0.2")
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        
        self.is_mini_mode = not self.is_mini_mode
        self.show()

    def populate_initial_data(self, history):
        """Remplit la table avec le cache JSON au démarrage."""
        self.results_table.setRowCount(0)
        for entry in history:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(entry['filename']))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(entry['score'])))
            
            verdict = "Fake HQ" if entry['score'] > 0.5 else "Original"
            color = "#FF3D00" if verdict == "Fake HQ" else "#76FF03"
            
            item_verdict = QTableWidgetItem(verdict)
            item_verdict.setForeground(QColor(color))
            self.results_table.setItem(row, 2, item_verdict)
