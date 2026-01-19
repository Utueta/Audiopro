"""
Audiopro Industrial Gauges v0.2.5
- Custom QWidget-based circular gauges
- High-performance vector rendering via QPainter
- Real-time value interpolation for telemetry
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont

class IndustrialGauge(QWidget):
    """
    Circular gauge for visualizing hardware metrics (GPU/VRAM).
    Features dynamic coloring: Green (Safe) -> Orange (Warn) -> Red (Critical).
    """
    def __init__(self, label="METRIC", parent=None):
        super().__init__(parent)
        self.label = label
        self.value = 0  # 0 to 100
        self.setMinimumSize(120, 120)

    def set_value(self, value):
        """Updates the gauge value and triggers a repaint."""
        self.value = max(0, min(100, value))
        self.update()

    def paintEvent(self, event):
        """Custom drawing logic for the industrial gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        side = min(width, height)
        
        # Define Rects
        rect = QRectF(10, 10, side - 20, side - 20)
        
        # 1. Draw Background Track
        track_pen = QPen(QColor("#2A2A2A"), 8)
        painter.setPen(track_pen)
        painter.drawArc(rect, -50 * 16, 280 * 16)

        # 2. Determine Color based on Value
        if self.value < 70:
            color = QColor("#00E676") # Neon Green
        elif self.value < 90:
            color = QColor("#FFAB40") # Amber
        else:
            color = QColor("#FF5252") # Coral Red

        # 3. Draw Value Arc
        value_pen = QPen(color, 8)
        value_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(value_pen)
        
        # Calculate span angle (280 degrees total range)
        span_angle = int((self.value / 100.0) * 280)
        # Start at 230 degrees (roughly 7 o'clock)
        painter.drawArc(rect, 230 * 16, -span_angle * 16)

        # 4. Draw Center Text
        painter.setPen(QColor("#E0E0E0"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{int(self.value)}%")
        
        # 5. Draw Label (Bottom)
        painter.setFont(QFont("Segoe UI", 8))
        label_rect = QRectF(0, side - 25, width, 20)
        painter.drawText(label_rect, Qt.AlignCenter, self.label)
