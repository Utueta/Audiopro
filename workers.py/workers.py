#"""
# Audiopro v0.3.1
# - Handles asynchronous worker execution and monitored utilization.
#"""

import logging
import traceback
import threading

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QEventLoop, QThreadPool

logger = logging.getLogger("system.workers")

_ACTIVE_WORKERS = 0
_ACTIVE_LOCK = threading.Lock()


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    result = Signal(object)  # Now sends AnalysisResult Data Contract
    error = Signal(str)
    progress = Signal(int)
    finished = Signal()

class AnalysisWorker(QRunnable):
    """
    Worker thread for audio analysis.
    Supports cancellation tokens for graceful shutdown.
    """
    def __init__(self, manager, file_path: str):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    @Slot()
    def run(self):
        global _ACTIVE_WORKERS
        with _ACTIVE_LOCK:
            _ACTIVE_WORKERS += 1

        if self._is_cancelled:
            return
            
        try:
            # AuditManager handles the 0.35-0.75 arbitration logic internally
            # Returns a core.models.AnalysisResult object
            result = self.manager.audit_file(self.file_path)
            
            if not self._is_cancelled:
                self.signals.result.emit(result)
                
        except Exception:
            err_msg = traceback.format_exc()
            logger.error(f"Worker Failure: {err_msg}")
            self.signals.error.emit(err_msg)
        finally:
            self.signals.finished.emit()

class HardwareMonitorWorker(QRunnable):
    """Real-time system telemetry (GPU/RAM) with industrial 1Hz frequency."""
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.is_running = True

    @Slot()
    def run(self):
        global _ACTIVE_WORKERS
        with _ACTIVE_LOCK:
            _ACTIVE_WORKERS += 1

        import psutil
        import time
        try:
            import pynvml
            pynvml.nvmlInit()
            has_gpu = True
        except:
            has_gpu = False

        while self.is_running:
            try:
                stats = {
                    "cpu": psutil.cpu_percent(),
                    "ram": psutil.virtual_memory().percent,
                }
                if has_gpu:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    stats["gpu"] = (mem.used / mem.total) * 100
                
                self.signals.result.emit(stats)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Telemetry Error: {e}")
                break
