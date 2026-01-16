import traceback
from PySide6.QtCore import QRunnable, QObject, Signal, Slot

class AnalysisSignals(QObject):
    dsp_ready = Signal(dict)
    result = Signal(dict)
    error = Signal(tuple)
    finished = Signal()

class AnalysisWorker(QRunnable):
    def __init__(self, file_path, analyzer, model, llm=None):
        super().__init__()
        self.file_path, self.analyzer, self.model, self.llm = file_path, analyzer, model, llm
        self.signals = AnalysisSignals()

    @Slot()
    def run(self):
        try:
            # Etape 1 : DSP & Score initial
            metrics = self.analyzer.get_metrics(self.file_path)
            metrics['score'] = self.model.predict(metrics)
            self.signals.dsp_ready.emit(metrics)

            # Etape 2 : Arbitrage LLM
            metrics['analysis_text'] = ""
            if self.llm and self.llm.check_arbitration(metrics['score']):
                metrics['analysis_text'] = self.llm.analyze_anomaly(metrics)
            
            self.signals.result.emit(metrics)
        except Exception as e:
            self.signals.error.emit((e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()
