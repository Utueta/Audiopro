from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject
# ... autres imports ...

class AnalysisWorkerSignals(QObject):
    result = Signal(dict)
    finished = Signal()

class AnalysisWorker(QRunnable):
    def __init__(self, path, analyzer):
        super().__init__()
        self.path = path
        self.analyzer = analyzer
        self.signals = AnalysisWorkerSignals()

    def run(self):
        data = self.analyzer.get_metrics(self.path)
        self.signals.result.emit(data)
        self.signals.finished.emit()

class AudioApp:
    def __init__(self):
        # ... init existante ...
        self.threadpool = QThreadPool()
        print(f"🚀 Threads disponibles : {self.threadpool.maxThreadCount()}")

    def run_pipeline(self):
        folder = QFileDialog.getExistingDirectory(None, "Dossier")
        if not folder: return
        files = self._get_filtered_files(folder, self.view.combo_options.currentIndex())
        
        self.progress = QProgressDialog("Analyse Multithreadée...", "Stop", 0, len(files), self.view)
        self.completed_count = 0

        for path in files:
            worker = AnalysisWorker(path, self.analyzer)
            worker.signals.result.connect(self._on_analysis_result)
            self.threadpool.start(worker)

    def _on_analysis_result(self, data):
        self.results.append(data)
        self.model.add_to_queue(data)
        self._update_main_table(data)
        self.completed_count += 1
        self.progress.setValue(self.completed_count)
        if self.completed_count >= self.progress.maximum():
            self.start_llm_pipeline()

    def detect_duplicates(self):
        """Nettoyage intelligent : garde le fichier avec le meilleur bitrate et score."""
        self.view.table_dup.setRowCount(0)
        hashes = {}
        duplicates = []

        for res in self.results:
            h = res['hash']
            if h == "0": continue
            if h not in hashes:
                hashes[h] = res
            else:
                # Comparaison intelligente
                original = hashes[h]
                current = res
                # On garde celui qui a le plus haut bitrate ou le score le plus bas
                if current['meta']['bitrate'] > original['meta']['bitrate']:
                    duplicates.append(original)
                    hashes[h] = current
                else:
                    duplicates.append(current)
        
        # Affichage
        for d in duplicates:
            row = self.view.table_dup.rowCount()
            self.view.table_dup.insertRow(row)
            self.view.table_dup.setItem(row, 0, QTableWidgetItem(os.path.basename(d['path'])))
            self.view.table_dup.setItem(row, 1, QTableWidgetItem("Qualité Inférieure"))
            self.view.table_dup.setItem(row, 2, QTableWidgetItem(os.path.basename(hashes[d['hash']]['path'])))
