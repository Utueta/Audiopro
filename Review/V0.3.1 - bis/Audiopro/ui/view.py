"""
Audiopro Random Forest Brain v0.2.5
- Implements MLModelInterface for deterministic classification
- Handles feature vector normalization via Z-Score Scaler
- Manages persistent weight loading from .pkl artifacts
"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QTextEdit, QProgressBar, QFileDialog, 
                             QPushButton, QCheckBox)
from PySide6.QtCore import Qt, Signal
from .components.gauges import IndustrialGauge
from .components.mini_player import MiniAudioPlayer
from core.models import AnalysisResult

class AudioproDashboard(QMainWindow):
    """
    Main Presentation Layer: Expert Audit Interface.
    v0.3.1 Update: Implements user-selectable loading modes (Full vs. Stratified).
    Ref: ARCHITECTURE.md Section 4 & spec_detail.txt Section 2.3.
    """
    # Signals for orchestration (Hexagonal Ports)
    human_verdict_submitted = Signal(str, str) # Hash, Verdict
    refresh_brain_requested = Signal()
    start_analysis_requested = Signal(str, bool) # FilePath, IsSegmented

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Audiopro v0.3.1 | Sentinel Obsidian Pro")
        self.resize(1200, 800)
        self._setup_ui()

    def _setup_ui(self):
        """Initializes the industrial-grade UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Header & Controls
        header = QHBoxLayout()
        
        # Analysis Trigger
        self.btn_analyze = QPushButton("IMPORT & ANALYZE")
        self.btn_analyze.setFixedHeight(40)
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)
        
        # Loading Mode Toggle (Spec 2.3)
        # Replaces legacy 45s constraint with Full/Stratified choice
        self.check_segmented = QCheckBox("Enable Segmented Analysis (Stratified Sampling)")
        self.check_segmented.setToolTip(
            "Unchecked: Full Loading (Default - Processes entire duration)\n"
            "Checked: Stratified Sampling (30s intro, 10s mid, 10s outro, 5s random)"
        )
        self.check_segmented.setChecked(False) # Default per project spec is Full Loading
        
        header.addWidget(self.btn_analyze)
        header.addStretch()
        header.addWidget(self.check_segmented)
        main_layout.addLayout(header)

        # 2. Visualization Grid (Forensic Telemetry Gauges)
        gauge_layout = QHBoxLayout()
        self.snr_gauge = IndustrialGauge("SNR (dB)")
        self.clip_gauge = IndustrialGauge("CLIPPING")
        self.suspicion_gauge = IndustrialGauge("SUSPICION")
        
        gauge_layout.addWidget(self.snr_gauge)
        gauge_layout.addWidget(self.clip_gauge)
        gauge_layout.addWidget(self.suspicion_gauge)
        main_layout.addLayout(gauge_layout)

        # 3. Forensic Insights (AI Arbitration Justification Panel)
        self.insight_panel = QTextEdit()
        self.insight_panel.setReadOnly(True)
        self.insight_panel.setPlaceholderText("Forensic Intelligence Justification will appear here...")
        self.insight_panel.setObjectName("ForensicInsight")
        self.insight_panel.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: 'Consolas';")
        
        main_layout.addWidget(QLabel("AI ARBITRATION JUSTIFICATION:"))
        main_layout.addWidget(self.insight_panel)

        # 4. Media Player (Expert Review)
        self.player = MiniAudioPlayer()
        main_layout.addWidget(self.player)

    def display_results(self, result: AnalysisResult):
        """
        Updates the dashboard with forensic telemetry from the DSP/ML pipeline.
        Handles both ML-only and LLM-Arbitrated results.
        """
        self.snr_gauge.set_value(result.snr_value)
        self.clip_gauge.set_value(result.clipping_count)
        self.suspicion_gauge.set_value(result.suspicion_score * 100)
        
        # Display AI reasoning if arbitration occurred in the Gray Zone (0.4-0.7)
        if result.llm_involved:
            text = f"VERDICT: {result.llm_verdict}\n\nREASONING:\n{result.llm_justification}"
            self.insight_panel.setText(text)
        else:
            mode_str = "Segmented (Stratified)" if result.was_segmented else "Full Loading"
            self.insight_panel.setText(
                f"LOCAL VERDICT: {result.ml_classification}\n"
                f"Confidence: {result.ml_confidence:.2f}\n"
                f"Analysis Mode: {mode_str}"
            )

    def _on_analyze_clicked(self):
        """
        Handles file selection and emits analysis signal with the chosen loading mode.
        Ensures UI remains non-blocking by delegating to manager.py.
        """
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Audio File for Audit", 
            "", 
            "Audio Files (*.wav *.flac *.mp3 *.ogg)"
        )
        
        if path:
            # Sync player for expert review
            self.player.load_audio(path)
            
            # Extract state of the Loading Mode Checkbox
            use_segmented = self.check_segmented.isChecked()
            
            # Emit signal to Manager Orchestrator
            self.start_analysis_requested.emit(path, use_segmented)
