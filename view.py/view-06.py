import sys
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QProgressBar, QTextEdit, QFileDialog, 
                             QLabel, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QSize, Slot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class AudioAnalysisView(QMainWindow):
    """
    Interface Principale Audiopro - Style Obsidian Glow.
    Restaure l'esthétique V5 avec une gestion de signal PySide6.
    """
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.logger = logging.getLogger("Audiopro.UI")
        
        self.setWindowTitle("AUDIOPRO | CERTIFICATION ENGINE")
        self.resize(1200, 850)
        
        self._apply_global_style()
        self._init_ui()

    def _apply_global_style(self):
        """Application de la charte graphique Obsidian Glow demandée."""
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #0F111A; 
            }
            #statusLabel { 
                color: #00F2FF; 
                font-size: 26px; 
                font-weight: bold; 
                padding: 15px; 
            }
            QPushButton { 
                background: #1A1D26; 
                border: 1px solid #00F2FF; 
                color: white; 
                padding: 12px; 
                border-radius: 4px; 
                font-weight: bold; 
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QPushButton:hover { 
                background: #00F2FF; 
                color: #0F111A; 
            }
            QPushButton:disabled {
                border-color: #333333;
                color: #555555;
            }
            QTextEdit { 
                background: #161922; 
                color: #BBBBBB; 
                border: 1px solid #2A2D36;
                border-radius: 5px; 
                font-family: 'Consolas'; 
                padding: 10px; 
                font-size: 11px;
            }
            QProgressBar {
                background-color: #1A1D26;
                border: 1px solid #333333;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #00F2FF;
                border-radius: 5px;
            }
        """)

    def _init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- HEADER : Statut de Certification ---
        self.header_frame = QFrame()
        header_layout = QHBoxLayout(self.header_frame)
        
        self.status_label = QLabel("PRÊT POUR ANALYSE")
        self.status_label.setObjectName("statusLabel")
        header_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)
        
        self.main_layout.addWidget(self.header_frame)

        # --- GRAPHIQUES : Zone DSP ---
        self.graph_container = QFrame()
        self.graph_container.setStyleSheet("background: #161922; border-radius: 10px; border: 1px solid #2A2D36;")
        graph_layout = QVBoxLayout(self.graph_container)
        
        # Intégration Matplotlib avec fond adapté
        self.figure = Figure(figsize=(10, 6), facecolor='#161922')
        self.canvas = FigureCanvas(self.figure)
        self.ax_wave = self.figure.add_subplot(211, facecolor='#0F111A')
        self.ax_spec = self.figure.add_subplot(212, facecolor='#0F111A')
        
        # Nettoyage cosmétique des axes
        for ax in [self.ax_wave, self.ax_spec]:
            ax.tick_params(colors='#555555', labelsize=8)
            for spine in ax.spines.values(): spine.set_color('#2A2D36')
            
        graph_layout.addWidget(self.canvas)
        self.main_layout.addWidget(self.graph_container, stretch=3)

        # --- CONSOLE : Logs d'Audit ---
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Les logs d'analyse s'afficheront ici...")
        self.main_layout.addWidget(self.console, stretch=1)

        # --- FOOTER : Actions ---
        footer_layout = QHBoxLayout()
        
        self.btn_scan = QPushButton("SÉLECTIONNER FICHIER SOURCE")
        self.btn_scan.clicked.connect(self._on_select_file)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.hide()
        
        footer_layout.addWidget(self.btn_scan, 2)
        footer_layout.addWidget(self.progress_bar, 3)
        self.main_layout.addLayout(footer_layout)

    def _on_select_file(self):
        # Logique de sélection et thread worker (restaurée précédemment)
        pass

    @Slot(dict)
    def update_ui_with_results(self, results):
        """Mise à jour du style en fonction du verdict (Glow Dynamique)."""
        verdict = results.get('verdict', 'UNKNOWN')
        self.status_label.setText(f"VERDICT : {verdict}")
        
        if verdict == "GOOD":
            self.status_label.setStyleSheet("color: #00FF88;") # Vert Néon
        elif "BAN" in verdict:
            self.status_label.setStyleSheet("color: #FF0055;") # Rouge Néon
