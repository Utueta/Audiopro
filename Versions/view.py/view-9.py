from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QTextEdit, QSlider, QLabel
from PySide6.QtCore import Qt, Signal
from ui.components import SpectralWidget

class AudioExpertView(QMainWindow):
    scan_requested = Signal(str)
    feedback_given = Signal(str, str)

    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("AUDIO EXPERT PRO V0.2.4")
        self.resize(1100, 800)
        self.setAcceptDrops(True)
        self.current_hash = None
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("DÉPOSEZ UN FICHIER")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        
        # Inspection
        self.tab_spec = QWidget()
        spec_l = QVBoxLayout(self.tab_spec)
        self.spec_view = SpectralWidget()
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(5, 100); self.zoom.setValue(100)
        self.zoom.valueChanged.connect(self.spec_view.set_zoom)
        spec_l.addWidget(self.spec_view)
        spec_l.addWidget(self.zoom)
        self.tabs.addTab(self.tab_spec, "SPECTROGRAMME")

        # Rapport
        self.report = QTextEdit("Diagnostic...")
        self.tabs.addTab(self.report, "RAPPORT IA")
        layout.addWidget(self.tabs)

        # Verdicts
        v_layout = QHBoxLayout()
        self.btn_bon = QPushButton("BON ✅")
        self.btn_ban = QPushButton("DÉFECTUEUX ❌")
        self.btn_bon.clicked.connect(lambda: self._verdict("bon"))
        self.btn_ban.clicked.connect(lambda: self._verdict("ban"))
        v_layout.addWidget(self.btn_bon); v_layout.addWidget(self.btn_ban)
        layout.addLayout(v_layout)

    def handle_dsp_ready(self, res):
        self.current_hash = res['hash']
        self.status_label.setText(f"QUALITÉ : {res.get('quality_score', 0):.1f}%")
        if 'matrix' in res: self.spec_view.update_data(res['matrix'])

    def handle_analysis_result(self, res):
        self.report.setText(f"Score Suspicion: {res['score']:.2f}\n\n{res.get('analysis_text', '')}")

    def _verdict(self, tag):
        if self.current_hash: self.feedback_given.emit(self.current_hash, tag)

    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dropEvent(self, e):
        for url in e.mimeData().urls(): self.scan_requested.emit(url.toLocalFile())
