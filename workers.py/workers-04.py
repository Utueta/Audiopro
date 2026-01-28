#"""
# Audiopro v0.3.1
# - Handles asynchronous worker execution and monitored utilization.
#"""

from __future__ import annotations

import logging
import threading
import traceback
from typing import Any, Dict

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QThreadPool

logger = logging.getLogger("system.workers")

_ACTIVE_WORKERS = 0
_ACTIVE_LOCK = threading.Lock()


class WorkerSignals(QObject):
    """Signals emitted by background workers."""
    result = Signal(object)  # AnalysisResult or telemetry dict
    error = Signal(str)
    finished = Signal()


class AnalysisWorker(QRunnable):
    """Thread-safe execution wrapper for the analysis pipeline.

    Supports user-selected segmented vs full loading mode via the manager entrypoint:
      manager.audit_file(file_path, is_segmented=bool)
    """

    def __init__(self, manager: Any, file_path: str, is_segmented: bool):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.is_segmented = bool(is_segmented)
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        global _ACTIVE_WORKERS
        with _ACTIVE_LOCK:
            _ACTIVE_WORKERS += 1
        try:
            result = self.manager.audit_file(self.file_path, is_segmented=self.is_segmented)
            self.signals.result.emit(result)
        except Exception:
            err = traceback.format_exc()
            logger.error(f"Analysis Pipeline Failure: {err}")
            self.signals.error.emit(err)
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE_WORKERS -= 1
            self.signals.finished.emit()


def get_threadpool_utilization(pool: QThreadPool) -> Dict[str, int]:
    """Returns monitored threadpool utilization stats."""
    try:
        max_threads = int(pool.maxThreadCount())
    except Exception:
        max_threads = 0
    with _ACTIVE_LOCK:
        active = int(_ACTIVE_WORKERS)
    return {"active": active, "max": max_threads}
