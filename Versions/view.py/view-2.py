from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSlider, QLabel, QPushButton, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation
from PySide6.QtGui import QColor, QImage, QPixmap
import numpy as np

class AudioExpertView(QMainWindow):
    scan_requested = Signal(str)
    feedback_given = Signal(str, bool)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._pixmap_cache = None
        self.current_hash = None
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("AUDIO EXPERT PRO [OBSIDIAN]")
        self.resize(1100, 750)
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)

        # Moniteur Principal (Score & Glow)
        self.status_label = QLabel("DÉPOSEZ UN FICHIER AUDIO")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00F2FF;")
        self.layout.addWidget(self.status_label)
        
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(0)
        self.glow.setColor(QColor(0, 242, 255))
        self.status_label.setGraphicsEffect(self.glow)

        # Rapport LLM (Axe A)
        self.llm_report = QLabel("Expertise : En attente d'analyse...")
        self.llm_report.setWordWrap(True)
        self.llm_report.setStyleSheet("background: #1A1C25; padding: 15px; border-radius: 5px; color: #BBBBBB;")
        self.layout.addWidget(self.llm_report)

        # Inspection Spectrale (Axe B)
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("ZOOM SPECTRAL :"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(5, 100)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        self.layout.addLayout(zoom_layout)

        # Zone de Contrôle (Axe C)
        ctrl_layout = QHBoxLayout()
        self.btn_valid = QPushButton("✅ SCORE CORRECT")
        self.btn_fraud = QPushButton("❌ ERREUR IA")
        self.btn_valid.clicked.connect(lambda: self.submit_feedback(True))
        self.btn_fraud.clicked.connect(lambda: self.submit_feedback(False))
        ctrl_layout.addWidget(self.btn_valid)
        ctrl_layout.addWidget(self.btn_fraud)
        self.layout.addLayout(ctrl_layout)

    def handle_dsp_ready(self, res):
        """Axe A : Affichage immédiat du spectrogramme."""
        self.current_hash = res['hash']
        self.status_label.setText(f"SCORE PRÉSUMÉ : {res['score']:.2f}")
        
        # Axe B : Création du cache image
        matrix = res['matrix']
        norm = ((matrix - matrix.min()) / (matrix.max() - matrix.min()) * 255).astype(np.uint8)
        self._pixmap_cache = QImage(norm.data, norm.shape[1], norm.shape[0], norm.shape[1], QImage.Format_Grayscale8)
        self._trigger_glow(res['score'] > 0.6)

    def handle_analysis_result(self, res):
        """Mise à jour finale avec texte LLM."""
        self.llm_report.setText(f"VERDICT LLM : {res['analysis_text'] or 'Analyse DSP Pure.'}")

    def on_zoom_changed(self, val):
        if self._pixmap_cache:
            # Ici la logique de scale du pixmap natif
            pass 

    def submit_feedback(self, is_valid):
        if self.current_hash:
            self.feedback_given.emit(self.current_hash, is_valid)
            self.status_label.setText("FEEDBACK ENREGISTRÉ")

    def _trigger_glow(self, active):
        if hasattr(self, 'anim'): self.anim.stop()
        self.anim = QPropertyAnimation(self.glow, b"blurRadius")
        self.anim.setEndValue(25 if active else 0)
        self.anim.setDuration(800)
        self.anim.start()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()
    def dropEvent(self, e):
        for url in e.mimeData().urls(): self.scan_requested.emit(url.toLocalFile())
