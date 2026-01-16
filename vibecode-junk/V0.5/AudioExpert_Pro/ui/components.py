from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtCore import Qt
import numpy as np

class SpectralWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(280)
        self.matrix = None
        self.zoom_level = 1.0

    def update_data(self, matrix):
        self.matrix = matrix
        self.update()

    def set_zoom(self, value):
        self.zoom_level = value / 100.0
        self.update()

    def paintEvent(self, event):
        if self.matrix is None: return
        painter = QPainter(self)
        h, w = self.matrix.shape
        # Logique de zoom : sélection de la portion temporelle (colonnes)
        view_w = int(w * self.zoom_level)
        norm = ((self.matrix[:, :view_w] + 80) / 80 * 255).clip(0, 255).astype(np.uint8)
        img = QImage(norm.data, view_w, h, view_w, QImage.Format_Grayscale8)
        painter.drawPixmap(self.rect(), QPixmap.fromImage(img))

