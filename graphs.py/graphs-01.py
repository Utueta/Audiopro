"""
Audiopro Forensic Visualization v0.3.1
- Renders the 'Suspicion Zone' and historical analysis telemetry.
- Integrated with PySide6 and Matplotlib.
"""
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ForensicGraph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.fig = Figure(facecolor='#0F111A')
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.ax = self.fig.add_subplot(111)
        self._init_theme()

    def _init_theme(self):
        self.ax.set_facecolor('#161925')
        self.ax.tick_params(colors='#888EAB', labelsize=8)
        self.fig.tight_layout()

    def update_data(self, history):
        self.ax.clear()
        self._init_theme()
        # Visual logic for SNR vs Clipping history
        self.canvas.draw()
