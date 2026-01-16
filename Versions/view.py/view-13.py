from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QUrl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MainView(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Expert Pro V4.1 - Expert Mode")
        self.setMinimumSize(1250, 850)
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Définition des 3 onglets principaux
        self.tab_scan = QWidget()
        self.tab_review = QWidget()
        self.tab_duplicates = QWidget()
        
        self.tabs.addTab(self.tab_scan, "🚀 Scan Pipeline")
        self.tabs.addTab(self.tab_review, "🎧 Révision & Player")
        self.tabs.addTab(self.tab_duplicates, "👯 Doublons")

        self._setup_scan_tab()
        self._setup_review_tab()
        self._setup_duplicates_tab() # Appliqué ici

    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        self.combo_options = QComboBox()
        self.combo_options.addItems([
            "0: 100 Premiers", 
            "1: Personnalisé", 
            "2: TOUS (Nouveaux)", 
            "3: TOUS + Refresh Bon"
        ])
        self.btn_start = QPushButton("Lancer l'Analyse")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Fichier", "Score ML", "Status", "Timestamp Erreur"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(QLabel("Configuration du Scan :"))
        layout.addWidget(self.combo_options)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.table)
        layout.addWidget(self.log)

    def _setup_review_tab(self):
        layout = QHBoxLayout(self.tab_review)
        
        # Zone Graphique (Waveform)
        left = QVBoxLayout()
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        left.addWidget(self.canvas)
        
        # Zone de Contrôle
        right = QVBoxLayout()
        self.info_lab = QLabel("Sélectionnez un fichier suspect")
        self.btn_play_err = QPushButton("▶️ Écouter l'erreur")
        self.btn_good = QPushButton("✅ [B]on Quality")
        self.btn_bad = QPushButton("❌ [D]éfectueux (Ban)")
        self.btn_skip = QPushButton("⏭️ [S]auter")
        
        right.addWidget(self.info_lab)
        right.addWidget(self.btn_play_err)
        right.addWidget(self.btn_good)
        right.addWidget(self.btn_bad)
        right.addWidget(self.btn_skip)
        right.addStretch()
        
        layout.addLayout(left, 2)
        layout.addLayout(right, 1)

    def _setup_duplicates_tab(self):
        """Implémentation de l'interface Doublons (Point 3 de la mise à jour)"""
        layout = QVBoxLayout(self.tab_duplicates)
        
        # Stats et Titre
        self.label_dup_stats = QLabel("Scannez un dossier pour identifier les doublons.")
        self.label_dup_stats.setStyleSheet("font-weight: bold; color: #e67e22; font-size: 14px;")
        
        # Tableau des Doublons
        self.table_dup = QTableWidget(0, 3)
        self.table_dup.setHorizontalHeaderLabels(["Fichier Doublon", "Type de Relation", "Fichier Original"])
        self.table_dup.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_dup.setAlternatingRowColors(True)
        
        # Bouton d'action massive
        self.btn_clean_duplicates = QPushButton("🗑️ Marquer les doublons pour suppression")
        self.btn_clean_duplicates.setStyleSheet("background-color: #d35400; color: white; padding: 10px; font-weight: bold;")
        
        layout.addWidget(self.label_dup_stats)
        layout.addWidget(self.table_dup)
        layout.addWidget(self.btn_clean_duplicates)

    def update_waveform(self, y, ts_sample):
        self.ax.clear()
        self.ax.plot(y, color='#1f77b4', alpha=0.7)
        if ts_sample > 0:
            self.ax.axvline(x=ts_sample, color='red', linestyle='--', label='Erreur')
        self.canvas.draw_idle()
