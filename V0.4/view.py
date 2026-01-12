import sys
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QProgressBar, QFrame, QScrollArea)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QPalette

class AudioExpertView(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle(f"Audio Expert Pro - {config['project_info']['version']}")
        self.setMinimumSize(1000, 700)
        self._init_ui()

    def _init_ui(self):
        """Initialise le dashboard style Obsidian."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Section Jauge de Suspicion (Glow Bar)
        self.glow_label = QLabel("INDICE DE SUSPICION (AI)")
        self.glow_bar = QProgressBar()
        self.glow_bar.setRange(0, 100)
        self.glow_bar.setFixedHeight(25)
        self.glow_bar.setTextVisible(True)
        
        self.layout.addWidget(self.glow_label)
        self.layout.addWidget(self.glow_bar)
        
        # Zone des résultats détaillés
        self.result_text = QLabel("Prêt pour l'analyse...")
        self.result_text.setAlignment(Qt.AlignTop)
        self.layout.addWidget(self.result_text)

    @Slot(dict)
    def handle_analysis_result(self, results):
        """Met à jour l'interface avec les scores de la V0.2.4."""
        score = results.get('score', 0.5)
        percentage = int(score * 100)
        
        # 1. Mise à jour de la jauge Glow
        self.glow_bar.setValue(percentage)
        
        # 2. Logique de coloration dynamique (Obsidian Palette)
        if score >= 0.7:
            # Fraude probable (Rouge)
            color = "#ff4444" 
            verdict = "⚠️ FRAUDE DÉTECTÉE (UP SCALED)"
        elif score >= 0.3:
            # Doute (Orange)
            color = "#ffaa00"
            verdict = "🧐 ANALYSE AMBIGUË"
        else:
            # Sain (Cyan Obsidian)
            color = "#00ffcc"
            verdict = "✅ FICHIER AUTHENTIQUE"

        # Application du style
        self.glow_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)
        
        # 3. Affichage des métriques détaillées
        info = (
            f"Verdict : {verdict}\n"
            f"Fichier : {os.path.basename(results['path'])}\n"
            f"Coupure Spectrale : {results['cut_off']:.1f} Hz\n"
            f"SNR : {results['snr']:.2f} dB\n"
            f"Bitrate : {results['bitrate']} kbps\n"
            f"Arbitrage IA : {results.get('ai_verdict', 'N/A')}"
        )
        self.result_text.setText(info)
