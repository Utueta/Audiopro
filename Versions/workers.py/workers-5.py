from PySide6.QtCore import QRunnable, QObject, Signal, Slot
import traceback

class AnalysisSignals(QObject):
    dsp_ready = Signal(dict)
    result = Signal(dict)
    error = Signal(tuple)

class AnalysisWorker(QRunnable):
    def __init__(self, file_path, analyzer, model, llm):
        super().__init__()
        self.file_path, self.analyzer, self.model, self.llm = file_path, analyzer, model, llm
        self.signals = AnalysisSignals()

    @Slot()
    def run(self):
        try:
            m = self.analyzer.get_metrics(self.file_path)
            m['score'] = self.model.predict(m)
            self.signals.dsp_ready.emit(m)
            
            m['analysis_text'] = ""
            if self.llm and self.llm.check_arbitration(m['score']):
                m['analysis_text'] = self.llm.analyze_anomaly(m)
            
            self.signals.result.emit(m)
        except Exception as e:
            self.signals.error.emit((e, traceback.format_exc()))

