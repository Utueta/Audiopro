
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

