"""
Audiopro Random Forest Brain v0.2.5
- Implements MLModelInterface for deterministic classification
- Handles feature vector normalization via Z-Score Scaler
- Manages persistent weight loading from .pkl artifacts
"""

import numpy as np
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

logger = logging.getLogger("system.ui.graphs")

class ForensicGraph(QWidget):
    """
    Visualizes the 'Suspicion Zone' based on ML Triage thresholds.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Create Matplotlib Figure
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor='#0F111A')
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)
        
        self.ax = self.fig.add_subplot(111)
        self._init_plot()

    def _init_plot(self):
        """Sets the industrial theme for the plot."""
        self.ax.set_facecolor('#161925')
        self.ax.tick_params(colors='#888EAB', labelsize=8)
        self.ax.set_xlabel("SNR (dB)", color='#888EAB', fontsize=9)
        self.ax.set_ylabel("Clipping Samples", color='#888EAB', fontsize=9)
        self.ax.spines['bottom'].set_color('#1E2233')
        self.ax.spines['left'].set_color('#1E2233')
        self.fig.tight_layout()

    def update_data(self, history: list):
        """
        Plots historical data points. 
        Points are colored by verdict: Green (Clean), Red (Corrupt).
        """
        self.ax.clear()
        self._init_plot()

        if not history:
            self.canvas.draw()
            return

        snr = [d.get('snr', 0) for d in history]
        clipping = [d.get('clipping', 0) for d in history]
        verdicts = [d.get('verdict', 'UNKNOWN') for d in history]

        colors = []
        for v in verdicts:
            if v == "CLEAN": colors.append('#76FF03')
            elif v == "CORRUPT": colors.append('#FF3D00')
            else: colors.append('#FFAB40')

        self.ax.scatter(snr, clipping, c=colors, s=30, edgecolors='white', linewidth=0.5)
        
        # Draw Triage Zone (Heuristic Visual Aid)
        self.ax.axvspan(0, 15, color='#FF3D00', alpha=0.1, label="Risk Zone")
        
        self.canvas.draw()
        logger.debug("Forensic graph updated with latest session history.")
