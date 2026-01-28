#"""
# Audiopro v0.3.1
# - Handles the expert UI dashboard and telemetry view.
#"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QFileDialog, QLabel, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer

from core.models import AnalysisResult
from core.telemetry import get_resource_snapshot

# NOTE: components are project-specific; imported lazily to avoid import-time failures
from ui.components.gauges import IndustrialGauge
from ui.components.mini_player import MiniAudioPlayer


class AudioproDashboard(QMainWindow):
    """Expert UI for Audiopro v0.3.1.

    Implements mandatory segmented loading toggle.
    """
    start_analysis_requested = Signal(str, bool)

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

        header = QHBoxLayout()
        self.btn_analyze = QPushButton("IMPORT & ANALYZE")
        self.btn_analyze.setFixedHeight(40)
        self.btn_analyze.clicked.connect(self._on_analyze_clicked)

        self.check_segmented = QCheckBox("Enable Segmented Analysis (Stratified Sampling)")
        self.check_segmented.setChecked(False)
        self.check_segmented.setToolTip("Unchecked: Full Loading\nChecked: 30s/10s/10s/5s Sampling")

        header.addWidget(self.btn_analyze)
        header.addStretch()
        header.addWidget(self.check_segmented)
        main_layout.addLayout(header)

        gauge_layout = QHBoxLayout()
        self.snr_gauge = IndustrialGauge("SNR (dB)")
        self.clip_gauge = IndustrialGauge("CLIPPING")
        self.suspicion_gauge = IndustrialGauge("SUSPICION")
        gauge_layout.addWidget(self.snr_gauge)
        gauge_layout.addWidget(self.clip_gauge)
        gauge_layout.addWidget(self.suspicion_gauge)
        main_layout.addLayout(gauge_layout)

        self.insight_panel = QTextEdit()
        self.insight_panel.setReadOnly(True)
        self.insight_panel.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc;")
        main_layout.addWidget(QLabel("FORENSIC INTELLIGENCE JUSTIFICATION:"))
        main_layout.addWidget(self.insight_panel)

        self.player = MiniAudioPlayer()
        main_layout.addWidget(self.player)

    def _setup_resource_monitoring(self) -> None:
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
        self.snr_gauge.set_value(float(result.snr_value))
        self.clip_gauge.set_value(int(result.clipping_count))
        self.suspicion_gauge.set_value(float(result.suspicion_score) * 100.0)

        if bool(getattr(result, "llm_involved", False)):
            self.insight_panel.setText(f"VERDICT: {result.llm_verdict}\n\nREASONING:\n{result.llm_justification}")
        else:
            mode = "Segmented" if bool(getattr(result, "was_segmented", False)) else "Full"
            self.insight_panel.setText(f"LOCAL VERDICT: {result.ml_classification} ({mode} Mode)")

    def _on_analyze_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Audio File")
        if path:
            self.player.load_audio(path)
            is_segmented = bool(self.check_segmented.isChecked())
            self.start_analysis_requested.emit(path, is_segmented)
