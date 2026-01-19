"""
Audiopro Main Dashboard v0.3.1
- Presentation Layer: Industrial PySide6 Dashboard.
- v0.3.1: Integrated Forensic Insight Panel for AI Justification.
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QProgressBar, QFileDialog, QPushButton)
from PySide6.QtCore import Qt, Signal
from .components.gauges import IndustrialGauge
from .components.mini_player import MiniAudioPlayer
from core.models import AnalysisResult

class AudioproDashboard(QMainWindow):
    human_verdict_submitted = Signal(str, str) # Hash, Verdict
    refresh_brain_requested = Signal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Audiopro v0.3.1 | Sentinel Obsidian Pro")
        self.resize(1200, 800)
        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Header & Controls
        header = QHBoxLayout()
        self.btn_analyze = QPushButton("IMPORT & ANALYZE")
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)
        header.addWidget(self.btn_analyze)
        main_layout.addLayout(header)

        # 2. Visualization Grid (Gauges)
        gauge_layout = QHBoxLayout()
        self.snr_gauge = IndustrialGauge("SNR (dB)")
        self.clip_gauge = IndustrialGauge("CLIPPING")
        self.suspicion_gauge = IndustrialGauge("SUSPICION")
        gauge_layout.addWidget(self.snr_gauge)
        gauge_layout.addWidget(self.clip_gauge)
        gauge_layout.addWidget(self.suspicion_gauge)
        main_layout.addLayout(gauge_layout)

        # 3. Forensic Insights (v0.3.1 Addition)
        self.insight_panel = QTextEdit()
        self.insight_panel.setReadOnly(True)
        self.insight_panel.setPlaceholderText("Forensic Intelligence Justification will appear here...")
        self.insight_panel.setObjectName("ForensicInsight")
        main_layout.addWidget(QLabel("AI ARBITRATION JUSTIFICATION:"))
        main_layout.addWidget(self.insight_panel)

        # 4. Media Player
        self.player = MiniAudioPlayer()
        main_layout.addWidget(self.player)

    def display_results(self, result: AnalysisResult):
        """Updates the dashboard with forensic telemetry."""
        self.snr_gauge.set_value(result.snr_value)
        self.clip_gauge.set_value(result.clipping_count)
        self.suspicion_gauge.set_value(result.suspicion_score * 100)
        
        # Display AI reasoning if arbitration occurred
        if result.llm_involved:
            text = f"VERDICT: {result.llm_verdict}\n\nREASONING:\n{result.llm_justification}"
            self.insight_panel.setText(text)
        else:
            self.insight_panel.setText(f"LOCAL VERDICT: {result.ml_classification} (Confidence: {result.ml_confidence:.2f})")

    def _on_analyze_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Audio File")
        if path:
            self.player.load_audio(path)
            # In practice, this triggers the manager.route_analysis via a worker
