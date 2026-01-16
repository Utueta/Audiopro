from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, Signal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MainView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Expert Pro V4")
        self.resize(1300, 900)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.setup_analyse_tab()
        self.setup_results_tab()
        self.setup_review_tab()

    def setup_analyse_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.btn_browse = QPushButton("📁 Sélectionner Dossier")
        self.progress = QProgressBar()
        self.log = QTextEdit(); self.log.setReadOnly(True)
        layout.addWidget(self.btn_browse); layout.addWidget(self.progress); layout.addWidget(self.log)
        self.tabs.addTab(tab, "📊 Analyse")

    def setup_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Fichier", "Score Qualité", "ML Suspicion", "Type HQ", "Tag"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.tabs.addTab(tab, "📋 Résultats")

    def setup_review_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.lbl_current = QLabel("Sélectionnez un fichier pour révision")
        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.canvas = FigureCanvas(self.fig)
        
        btn_layout = QHBoxLayout()
        self.btn_good = QPushButton("✅ BON"); self.btn_bad = QPushButton("❌ DÉFECTUEUX")
        btn_layout.addWidget(self.btn_good); btn_layout.addWidget(self.btn_bad)
        
        layout.addWidget(self.lbl_current)
        layout.addWidget(self.canvas)
        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "🎧 Révision")
