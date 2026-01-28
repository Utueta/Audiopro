import sys
import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont

class ObsidianSplashScreen(QWidget):
    """
    Splashscreen Premium - Style Obsidian Glow.
    Gère l'initialisation système avec une esthétique Cyber-Audit.
    """
    def __init__(self, on_complete_callback):
        super().__init__()
        self.on_complete = on_complete_callback
        
        # Configuration de la fenêtre
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 350)

        self._init_ui()
        self._apply_obsidian_glow()
        
        # Timer d'initialisation simulée (à lier au manager plus tard)
        self.counter = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(30)

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)

        # Container Principal
        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        self.container_layout = QVBoxLayout(self.container)
        
        # Logo / Titre
        self.title = QLabel("AUDIOPRO")
        self.title.setObjectName("Title")
        self.title.setFont(QFont("Segoe UI", 40, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)

        self.subtitle = QLabel("CERTIFICATION ENGINE | V1.0")
        self.subtitle.setObjectName("Subtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress.setObjectName("ProgressBar")
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)

        # Statut
        self.status = QLabel("Initialisation des modules DSP...")
        self.status.setObjectName("Status")
        self.status.setAlignment(Qt.AlignCenter)

        self.container_layout.addWidget(self.title)
        self.container_layout.addWidget(self.subtitle)
        self.container_layout.addSpacing(40)
        self.container_layout.addWidget(self.progress)
        self.container_layout.addWidget(self.status)
        
        self.layout.addWidget(self.container)

    def _apply_obsidian_glow(self):
        """Application du CSS Obsidian Glow (Style V5)."""
        self.setStyleSheet("""
            #MainContainer {
                background-color: #1a1a1a;
                border-radius: 15px;
                border: 1px solid #333333;
            }
            #Title {
                color: #ffffff;
                letter-spacing: 5px;
                margin-top: 20px;
            }
            #Subtitle {
                color: #00d1ff;
                font-family: 'Consolas';
                font-weight: bold;
            }
            #Status {
                color: #888888;
                font-family: 'Consolas';
                font-size: 11px;
                margin-top: 10px;
            }
            #ProgressBar {
                background-color: #0d0d0d;
                border-radius: 5px;
                border: none;
            }
            #ProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                  stop:0 #0055ff, stop:1 #00d1ff);
                border-radius: 5px;
            }
        """)

        # Effet de lueur (Glow) sur le titre
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(25)
        glow.setColor(QColor(0, 209, 255, 150))
        glow.setOffset(0, 0)
        self.title.setGraphicsEffect(glow)

    def _update_progress(self):
        self.counter += 1
        self.progress.setValue(self.counter)
        
        if self.counter == 30:
            self.status.setText("Chargement du modèle Brain (ML)...")
        if self.counter == 60:
            self.status.setText("Connexion à l'arbitre LLM Qwen...")
        if self.counter == 90:
            self.status.setText("Système prêt.")

        if self.counter >= 100:
            self.timer.stop()
            self._fade_out()

    def _fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.finished.connect(self.on_complete)
        self.animation.start()
