import sys, json, os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from analyzer import AudioAnalyzer
from model import AudioModel
from view import MainView

class AnalysisWorker(QRunnable):
    class Signals(QObject):
        result = Signal(dict)
    def __init__(self, path, analyzer):
        super().__init__()
        self.path, self.analyzer, self.signals = path, analyzer, self.Signals()
    def run(self):
        self.signals.result.emit(self.analyzer.get_metrics(self.path))

class AudioApp:
    def __init__(self):
        with open('config.json', 'r') as f: self.config = json.load(f)
        self.model = AudioModel(self.config['paths']['db_name'])
        self.analyzer = AudioAnalyzer(self.config)
        self.view = MainView()
        self.threadpool = QThreadPool()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.results = []
        self._connect_signals()

    def _connect_signals(self):
        self.view.btn_start.clicked.connect(self.run_pipeline)
        self.view.btn_clean_duplicates.clicked.connect(self.clean_duplicates)
        self.view.table.itemSelectionChanged.connect(self.load_selection)
        self.view.btn_good.clicked.connect(lambda: self.save_decision("Bon"))
        self.view.btn_bad.clicked.connect(lambda: self.save_decision("Ban"))

    def run_pipeline(self):
        folder = QFileDialog.getExistingDirectory(None, "Sélectionner Dossier")
        if not folder: return
        exts = tuple(self.config['audio']['extensions'])
        files = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if f.lower().endswith(exts)]
        
        self.results = []
        self.view.table.setRowCount(0)
        self.progress = QProgressDialog("Analyse Parallèle...", "Stop", 0, len(files), self.view)
        
        for path in files:
            worker = AnalysisWorker(path, self.analyzer)
            worker.signals.result.connect(self.on_result)
            self.threadpool.start(worker)

    def on_result(self, data):
        # Prédiction ML proactive
        data['ml_score'] = self.model.predict_suspicion(data)
        self.results.append(data)
        self.model.add_to_queue(data)
        
        row = self.view.table.rowCount()
        self.view.table.insertRow(row)
        self.view.table.setItem(row, 1, QTableWidgetItem(os.path.basename(data['path'])))
        self.view.table.setItem(row, 2, QTableWidgetItem(f"{data['ml_score']:.4f}"))
        self.progress.setValue(len(self.results))

    def load_selection(self):
        row = self.view.table.currentRow()
        if row < 0: return
        res = self.results[row]
        ts = res['defect_timestamps'][0] if res.get('defect_timestamps') else 0
        self.view.update_visuals(res['path'], ts)
        self.player.setSource(QUrl.fromLocalFile(res['path']))

    def save_decision(self, label):
        row = self.view.table.currentRow()
        if row >= 0:
            self.model.mark_file(self.results[row]['path'], label)
            self.view.table.setItem(row, 3, QTableWidgetItem(label))

    def clean_duplicates(self):
        hashes = {}
        for r in self.results:
            h = r['hash']
            if h == "0": continue
            if h not in hashes: hashes[h] = r
            else:
                old = hashes[h]
                # On garde le meilleur bitrate
                to_remove = r if old['meta']['bitrate'] >= r['meta']['bitrate'] else old
                hashes[h] = r if old['meta']['bitrate'] < r['meta']['bitrate'] else old
                row = self.view.table_dup.rowCount()
                self.view.table_dup.insertRow(row)
                self.view.table_dup.setItem(row, 0, QTableWidgetItem(os.path.basename(to_remove['path'])))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ctrl = AudioApp()
    ctrl.view.show()
    sys.exit(app.exec())
