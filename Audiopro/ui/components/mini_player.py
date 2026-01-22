"""
Audiopro v0.3.1
- Use Case: Compact industrial audio player with high-precision seeking.
- Logic: Integrates PySide6 Multimedia for forensic sample playback.
"""

import logging
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLabel
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QUrl

logger = logging.getLogger("system.ui.mini_player")

class MiniAudioPlayer(QWidget):
    """
    Compact industrial audio player with high-precision seeking.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_play.setObjectName("BtnMini")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("font-family: 'Consolas'; color: #00F2FF;")

        self.layout.addWidget(self.btn_play)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.lbl_time)

    def _connect_signals(self):
        self.btn_play.clicked.connect(self.toggle_playback)
        self.player.positionChanged.connect(self._update_position)
        self.player.durationChanged.connect(self._update_duration)
        self.slider.sliderMoved.connect(self._handle_seek)

    def load_audio(self, file_path: str):
        """Loads a forensic sample into the playback buffer."""
        self.player.setSource(QUrl.fromLocalFile(file_path))
        logger.info(f"Loaded audio for playback: {file_path}")

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def _update_position(self, pos):
        self.slider.setValue(pos)
        self._update_time_label()

    def _update_duration(self, duration):
        self.slider.setRange(0, duration)
        self._update_time_label()

    def _handle_seek(self, pos):
        self.player.setPosition(pos)

    def _update_time_label(self):
        curr = self.player.position() // 1000
        total = self.player.duration() // 1000
        self.lbl_time.setText(f"{curr//60:02d}:{curr%60:02d} / {total//60:02d}:{total%60:02d}")
