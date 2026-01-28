"""
Audiopro Industrial Gauges v0.3.1
- Custom QWidget-based circular gauges.
- High-performance vector rendering for hardware telemetry.
"""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen

class IndustrialGauge(QWidget):
    def __init__(self, label="METRIC", parent=None):
        super().__init__(parent)
        self.label = label
        self.value = 0
        self.setMinimumSize(120, 120)

    def set_value(self, value):
        self.value = max(0, min(100, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        rect = QRectF(10, 10, side - 20, side - 20)
        
        # Track
        painter.setPen(QPen(QColor("#2A2A2A"), 8))
        painter.drawArc(rect, -50 * 16, 280 * 16)

        # Dynamic Color
        color = QColor("#00E676") if self.value < 70 else QColor("#FFAB40") if self.value < 90 else QColor("#FF5252")
        
        # Value Arc
        value_pen = QPen(color, 8)
        value_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(value_pen)
        span_angle = int((self.value / 100.0) * 280)
        painter.drawArc(rect, 230 * 16, -span_angle * 16)
