"""
Audiopro Industrial UI v0.2.9
- Role: Data Presentation & User Interaction
- Logic: High-performance table updates and status management
- Integrity: Ensures unique rows via file_hash comparison
"""
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QStatusBar, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, Slot

# Note: This assumes you have the IndustrialGauge component in your project
from ui.components.gauges import IndustrialGauge 

class AudioproDashboard(QMainWindow):
    """
    Audiopro Industrial UI v0.2.9
    Centralized View for Audio Auditing, Hardware Telemetry, and Persistence.
    """
    # Signal emitted when a file is ready for the Manager to process
    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audiopro v0.2.9 | Industrial Audit Suite")
        self.resize(1300, 900)
        
        # Initialize UI Components
        self._apply_obsidian_style()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 1. Hardware Health Dashboard (Top Row)
        self.setup_telemetry_layout()
        
        # 2. Results Table (Middle Area)
        self.setup_table_headers()
        
        # 3. Footer & Status
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #888; border-top: 1px solid #333;")
        self.setStatusBar(self.status_bar)
        
        logging.info("UI: Industrial Dashboard v0.2.9 Initialized.")

    def _apply_obsidian_style(self):
        """Sets the Deep Obsidian aesthetic for low-light industrial environments."""
        self.setStyleSheet("""
            QMainWindow { background-color: #0F0F0F; }
            QWidget { font-family: 'Segoe UI', 'Roboto', sans-serif; }
            QTableWidget { 
                background-color: #1A1A1A; 
                color: #E0E0E0; 
                gridline-color: #2A2A2A; 
                border: 1px solid #333;
                selection-background-color: #2A2A2A;
            }
            QHeaderView::section { 
                background-color: #252525; 
                color: #AAA; 
                padding: 8px; 
                border: none;
                font-weight: bold;
            }
            QStatusBar { background-color: #0A0A0A; }
            QMessageBox { background-color: #1A1A1A; color: #EEE; }
        """)

    def setup_telemetry_layout(self):
        """Initializes the health gauges for system-wide monitoring."""
        t_layout = QHBoxLayout()
        self.cpu_gauge = IndustrialGauge(label="CPU UTIL")
        self.ram_gauge = IndustrialGauge(label="RAM USE")
        self.gpu_gauge = IndustrialGauge(label="GPU UTIL")
        self.vram_gauge = IndustrialGauge(label="VRAM USE")
        
        # Add gauges to layout
        for g in [self.cpu_gauge, self.ram_gauge, self.gpu_gauge, self.vram_gauge]:
            t_layout.addWidget(g)
        
        # Add stretch to keep gauges aligned to the left
        t_layout.addStretch()
        self.main_layout.addLayout(t_layout)

    def setup_table_headers(self):
        """
        Configures the Audit Results Table with Traceability features.
        Index: 0(HIDDEN HASH), 1(ID), 2(FILE), 3(VERDICT), 4(SNR), 5(CLIPPING), 6(SUSPICION)
        """
        self.results_table = QTableWidget(0, 7)
        headers = [
            "Full Hash",      # Internal ID (Hidden)
            "Short ID",       # Visual Traceability
            "File Name",      # Content Identifier
            "Verdict",        # AI/Security Status
            "SNR",            # Signal-to-Noise
            "Clipping",       # DSP Metric
            "Suspicion"       # Spectral Score
        ]
        self.results_table.setHorizontalHeaderLabels(headers)
        
        # Security Feature: Hide Full Hash from view but keep it for findItems() logic
        self.results_table.setColumnHidden(0, True) 
        
        # Configure Header Resizing
        h = self.results_table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Short ID
        h.setSectionResizeMode(2, QHeaderView.Stretch)          # File Name
        h.setSectionResizeMode(3, QHeaderView.Fixed)            # Verdict
        self.results_table.setColumnWidth(3, 120)

        # Interaction settings
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setSortingEnabled(True)
        
        self.main_layout.addWidget(self.results_table)

    # --- SLOTS FOR MANAGER COMMUNICATION ---

    @Slot(dict)
    def update_telemetry(self, stats: dict):
        """Updates the dashboard gauges and status bar with real-time health data."""
        self.cpu_gauge.update_value(stats.get('cpu', 0))
        self.ram_gauge.update_value(stats.get('ram', 0))
        self.gpu_gauge.update_value(stats.get('gpu', 0))
        self.vram_gauge.update_value(stats.get('vram', 0))
        
        # Disk I/O Activity shown in status bar to minimize visual clutter
        io_val = stats.get('disk_io', 0.0)
        self.status_bar.showMessage(f"System Operational | Disk I/O: {io_val:.1f} MB/s", 2000)

    @Slot(dict)
    def on_analysis_complete(self, data: dict):
        """Receives final arbitration from Manager and prepends to table."""
        self.add_audit_to_table(data, prepend=True)
        self.status_bar.showMessage(f"Audit Complete: {data['name']}", 5000)

    @Slot(str)
    def on_analysis_start(self, filename: str):
        """Provides immediate feedback when a file enters the pipeline."""
        self.status_bar.showMessage(f"Analyzing: {filename}...", 0)

    @Slot(str)
    def show_error_dialog(self, message: str):
        """Displays industrial alerts for security or hardware failures."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("System Alert")
        msg.setText(message)
        msg.exec()

    # --- DATA INSERTION LOGIC ---

    def add_audit_to_table(self, data: dict, prepend=False):
        """
        Inserts data into the table with deduplication and color-coding.
        Used for both historical sync (append) and live results (prepend).
        """
        # Integrity Check: Check Column 0 (Full Hash) for duplicates
        existing_rows = self.results_table.findItems(data['hash'], Qt.MatchExactly)
        if existing_rows:
            return

        row = 0 if prepend else self.results_table.rowCount()
        if prepend:
            self.results_table.insertRow(0)
        else:
            self.results_table.insertRow(row)

        # Column 0: Full Hash (Hidden)
        self.results_table.setItem(row, 0, QTableWidgetItem(data['hash']))
        
        # Column 1: Short ID
        self.results_table.setItem(row, 1, QTableWidgetItem(data['hash'][:8]))
        
        # Column 2: File Name
        self.results_table.setItem(row, 2, QTableWidgetItem(data['name']))
        
        # Column 3: Verdict (Color-Coded)
        v_item = QTableWidgetItem(data.get('verdict', 'UNKNOWN'))
        if data.get('verdict') == "SUSPICIOUS":
            v_item.setForeground(Qt.red)
        elif data.get('verdict') == "CLEAN":
            v_item.setForeground(Qt.green)
        self.results_table.setItem(row, 3, v_item)
        
        # Column 4-6: Metrics
        self.results_table.setItem(row, 4, QTableWidgetItem(f"{data.get('snr', 0):.2f} dB"))
        self.results_table.setItem(row, 5, QTableWidgetItem(str(data.get('clipping', 0))))
        self.results_table.setItem(row, 6, QTableWidgetItem(f"{data.get('suspicion', 0)*100:.1f}%"))
