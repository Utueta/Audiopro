#"""
# Audiopro v0.3.1
# - Handles the expert UI dashboard (Qt) including segmented loading toggle and resource telemetry.
#"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QFileDialog,
    QPushButton,
    QCheckBox,
)

from .components.gauges import IndustrialGauge
from .components.mini_player import MiniAudioPlayer
from core.models import AnalysisResult
from core.telemetry import get_resource_snapshot


class AudioproDashboard(QMainWindow):
    """Expert UI for Audiopro v0.3.1."""

    # UI → Orchestrator
    start_analysis_requested = Signal(str, object)  # (file_path, is_segmented: Optional[bool])

    # Orchestrator → UI
    human_verdict_submitted = Signal(str, str)  # (file_hash, verdict)
    refresh_brain_requested = Signal()

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Audiopro v0.3.1 | Sentinel Obsidian Pro")
        self.resize(1200, 800)

        self._setup_ui()
        self._setup_resource_monitoring()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header: Global Controls
        header = QHBoxLayout()
        self.btn_analyze = QPushButton("IMPORT & ANALYZE")
        self.btn_analyze.setFixedHeight(40)
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)

        # Loading Mode Toggle (Full is default)
        self.check_segmented = QCheckBox("Enable Segmented Analysis (Stratified Sampling)")
        self.check_segmented.setChecked(False)
        self.check_segmented.setToolTip("Unchecked: Full Loading\nChecked: 30s/10s/10s/5s Sampling")

        header.addWidget(self.btn_analyze)
        header.addStretch()
        header.addWidget(self.check_segmented)
        main_layout.addLayout(header)

        # Gauges
        gauge_layout = QHBoxLayout()
        self.snr_gauge = IndustrialGauge("SNR (dB)")
        self.clip_gauge = IndustrialGauge("CLIPPING")
        self.suspicion_gauge = IndustrialGauge("SUSPICION")
        gauge_layout.addWidget(self.snr_gauge)
        gauge_layout.addWidget(self.clip_gauge)
        gauge_layout.addWidget(self.suspicion_gauge)
        main_layout.addLayout(gauge_layout)

        # Insights
        self.insight_panel = QTextEdit()
        self.insight_panel.setReadOnly(True)
        self.insight_panel.setPlaceholderText("Forensic Intelligence Justification will appear here...")
        main_layout.addWidget(QLabel("FORENSIC INTELLIGENCE JUSTIFICATION:"))
        main_layout.addWidget(self.insight_panel)

        # Player
        self.player = MiniAudioPlayer()
        main_layout.addWidget(self.player)

    def _setup_resource_monitoring(self) -> None:
        """Periodic psutil/NVIDIA telemetry for UI monitoring."""
        self._resource_timer = QTimer(self)
        self._resource_timer.setInterval(1000)
        self._resource_timer.timeout.connect(self._poll_resources)
        self._resource_timer.start()

    def _poll_resources(self) -> None:
        try:
            db_path = None
            try:
                db_path = self.manager.config.get("paths", {}).get("db_path")
            except Exception:
                db_path = None

            snap = get_resource_snapshot(db_path=db_path)
            parts = [
                f"CPU {snap.cpu_percent:.0f}%",
                f"RAM {snap.ram_used_gb:.1f}/{snap.ram_total_gb:.1f} GB",
                f"IO R {snap.disk_read_mb_s:.1f} MB/s W {snap.disk_write_mb_s:.1f} MB/s",
            ]
            if snap.gpu_name:
                parts.append(f"GPU {snap.gpu_util_percent:.0f}% VRAM {snap.vram_used_mb:.0f}/{snap.vram_total_mb:.0f} MB")
            if snap.sqlite_wal_bytes is not None:
                parts.append(f"WAL {snap.sqlite_wal_bytes/1024/1024:.1f} MB")

            self.statusBar().showMessage(" | ".join(parts))
        except Exception:
            return

    def display_results(self, result: AnalysisResult) -> None:
        """Updates UI telemetry with result data."""
        self.snr_gauge.set_value(result.snr_value)
        self.clip_gauge.set_value(result.clipping_count)
        self.suspicion_gauge.set_value(result.suspicion_score * 100)

        if result.llm_involved:
            self.insight_panel.setText(f"VERDICT: {result.llm_verdict}\n\nREASONING:\n{result.llm_justification}")
        else:
            mode = "Segmented" if getattr(result, "was_segmented", False) else "Full"
            self.insight_panel.setText(f"LOCAL VERDICT: {result.ml_classification} ({mode} Mode)")

    def _on_analyze_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Audio File")
        if not path:
            return

        self.player.load_audio(path)
        is_segmented = bool(self.check_segmented.isChecked())
        self.start_analysis_requested.emit(path, is_segmented)
