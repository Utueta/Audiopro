from PySide6.QtCore import QRunnable, QObject, Signal
from core.models import AnalysisResult

class WorkerSignals(QObject):
    """Explicit thread affinity signals for UI safety."""
    result = Signal(AnalysisResult)  # Returns immutable Data Contract
    error = Signal(str)
    finished = Signal()

class AnalysisWorker(QRunnable):
    """Infrastructure bridge for offloading DSP to background threads."""
    def __init__(self, file_path: str, analyzer_func):
        super().__init__()
        self.file_path = file_path
        self.analyzer_func = analyzer_func
        self.signals = WorkerSignals()
        
        # Ensure the worker is cleaned up by Qt after execution
        self.setAutoDelete(True)

    def run(self):
        """Thread-safe execution block. Zero UI access permitted."""
        try:
            # Logic execution is fully isolated from Main Thread
            result = self.analyzer_func(self.file_path)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
