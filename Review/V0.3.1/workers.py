"""
Audiopro Async Workers v0.3.1
- Role: Multi-threaded execution of the Audit Pipeline.
- Logic: Wraps AuditManager in QRunnable to prevent UI blocking.
- Regressions: MAINTAINS Hardware Telemetry and Error Signaling.
"""

import logging
import traceback
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

logger = logging.getLogger("system.workers")

class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    result = Signal(dict)
    error = Signal(str)
    progress = Signal(int)
    finished = Signal()

class AnalysisWorker(QRunnable):
    """
    Worker thread for audio analysis.
    Executes the Manager's logic (Security -> Hash -> ML -> DB).
    """
    def __init__(self, manager, file_path: str):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            # Trigger the Manager's unified audit loop
            # This handles Security Gate, MD5, and ML Triage internally
            audit_data = self.manager.audit_file(self.file_path)
            
            if audit_data.get("verdict") == "REJECTED":
                self.signals.error.emit(f"Security: {self.file_path} rejected (Non-Audio).")
            else:
                self.signals.result.emit(audit_data)
                
        except Exception:
            err_msg = traceback.format_exc()
            logger.error(f"Worker Failure: {err_msg}")
            self.signals.error.emit(err_msg)
        finally:
            self.signals.finished.emit()

class HardwareMonitorWorker(QRunnable):
    """
    Background worker for real-time system telemetry (GPU/RAM).
    Maintains the industrial monitoring established in v0.2.8.
    """
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.is_running = True

    @Slot()
    def run(self):
        import psutil
        try:
            # Check for NVIDIA GPU Telemetry if available
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
                import time
                time.sleep(1) # Telemetry frequency: 1Hz
            except Exception as e:
                logger.error(f"Telemetry Error: {e}")
                break
