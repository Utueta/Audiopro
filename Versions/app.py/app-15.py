import sys, json, os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from analyzer import AudioAnalyzer
from model import AudioModel
from view import MainView

class AudioApp:
    def __init__(self):
        with open('config.json', 'r') as f: self.config = json.load(f)
        self.model = AudioModel(self.config['paths']['db_name'])
        self.analyzer = AudioAnalyzer(self.config)
        self.view = MainView()
        self.threadpool = QThreadPool()
        self.results = []
        self._connect_signals()

    def _connect_signals(self):
        self.view.btn_start.clicked.connect(self.run_pipeline)
        self.view.table.itemSelectionChanged.connect(self.load_selection)
        self.view.btn_good.clicked.connect(lambda: self.save_decision("Bon"))
        self.view.btn_bad.clicked.connect(lambda: self.save_decision("Ban"))

    def run_pipeline(self):
        folder = QFileDialog.getExistingDirectory(None, "Choisir dossier")
        if not folder: return
        files = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if f.lower().endswith(('.mp3', '.flac', '.wav'))]
        for path in files:
            worker = AnalysisWorker(path, self.analyzer)
            worker.signals.result.connect(self.on_result)
            self.threadpool.start(worker)

    def on_result(self, data):
        data['ml_score'] = self.model.predict_suspicion(data)
        self.results.append(data)
        self.model.add_to_queue(data)
        row = self.view.table.rowCount()
        self.view.table.insertRow(row)
        self.view.table.setItem(row, 1, QTableWidgetItem(os.path.basename(data['path'])))
        self.view.table.setItem(row, 2, QTableWidgetItem(f"{data['ml_score']:.3f}"))

    def load_selection(self):
        row = self.view.table.currentRow()
        if row >= 0:
            res = self.results[row]
            self.view.update_visuals(res['path'], 0)

    def save_decision(self, label):
        row = self.view.table.currentRow()
        if row >= 0:
            self.model.mark_file(self.results[row]['path'], label)
            self.view.table.setItem(row, 3, QTableWidgetItem(label))

class AnalysisWorker(QRunnable):
    class Signals(QObject): result = Signal(dict)
    def __init__(self, path, analyzer):
        super().__init__()
        self.path, self.analyzer, self.signals = path, analyzer, self.Signals()
    def run(self):
        self.signals.result.emit(self.analyzer.get_metrics(self.path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ctrl = AudioApp(); ctrl.view.show()
    sys.exit(app.exec())
