from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLabel
from PySide6.QtCore import Qt, Signal

class AudioExpertView(QMainWindow):
    scan_requested = Signal(str)
    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("AUDIO EXPERT PRO V0.2.4")
        self.resize(800, 600)
        self.setAcceptDrops(True)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.status = QLabel("GLISSEZ UN FICHIER")
        self.report = QTextEdit()
        layout.addWidget(self.status)
        layout.addWidget(self.report)

    def handle_analysis_result(self, res):
        self.status.setText(f"SCORE : {res['score']:.2f}")
        self.report.setText(res.get('analysis_text', "Analyse terminée."))

    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dropEvent(self, e):
        for url in e.mimeData().urls(): self.scan_requested.emit(url.toLocalFile())

