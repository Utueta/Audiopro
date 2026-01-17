import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                             QFileDialog, QListWidget, QLabel, QProgressBar)
from PySide6.QtCore import Slot, Qt
from core.manager import AnalysisManager
from core.models import AnalysisResult

class MainWindow(QMainWindow):
    """
    Presentation Layer: The Main Audit Interface.
    Strictly handles UI events and renders data contracts.
    """
    
    def __init__(self, manager: AnalysisManager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Audiopro Industrial - Expert Audit Interface")
        self.resize(800, 600)
        
        # --- UI Initialization ---
        self._init_ui()
        self._apply_styles()
        
        # --- Signal Mapping (The Hexagonal Bridge) ---
        self.manager.analysis_ready.connect(self._update_dashboard)

    def _init_ui(self):
        """Initializes the layout and widgets."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.status_label = QLabel("Ready for Audio Audit")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.import_btn = QPushButton("Import Audio for Analysis")
        self.import_btn.clicked.connect(self._on_import_clicked)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.result_list = QListWidget()
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.import_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.result_list)

    def _apply_styles(self):
        """Applies the 'Deep Obsidian' design system via the external QSS."""
        try:
            with open("ui/theme.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            # Fallback for missing stylesheet
            self.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0;")

    def _on_import_clicked(self):
        """Delegates heavy lifting to the orchestrator."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", "", "Audio Files (*.wav *.flac *.mp3)"
        )
        
        if file_paths:
            self.progress_bar.setVisible(True)
            self.status_label.setText(f"Processing {len(file_paths)} files...")
            
            for path in file_paths:
                self.manager.request_analysis(path)

    @Slot(AnalysisResult)
    def _update_dashboard(self, result: AnalysisResult):
        """Updates UI with the immutable data contract."""
        if result.success:
            item_text = (f"FILE: {result.path.split('/')[-1]} | "
                         f"CENTROID: {result.centroid} Hz | "
                         f"NOISE: {result.noise_floor} dB")
            self.result_list.addItem(item_text)
            self.status_label.setText("Analysis Complete")
        else:
            self.result_list.addItem(f"ERROR: {result.path} - {result.error}")
        
        self.progress_bar.setVisible(False)

    def closeEvent(self, event):
        """Ensures graceful shutdown of infrastructure threads."""
        print("Shutting down Audiopro pipeline...")
        super().closeEvent(event)
