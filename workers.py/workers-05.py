#"""
# Audiopro v0.3.1
# - Handles asynchronous worker execution and monitored utilization.
#"""

from __future__ import annotations

import logging
import threading
import traceback
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QThreadPool

logger = logging.getLogger("system.workers")

_ACTIVE_WORKERS = 0
_ACTIVE_LOCK = threading.Lock()


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    result = Signal(object)   # core.models.AnalysisResult
    error = Signal(str)
    finished = Signal()


class AnalysisWorker(QRunnable):
    """Thread-safe execution wrapper for the analysis pipeline.

    Passes loading mode preference (segmented/full) to the orchestrator.
    """

    def __init__(self, manager, file_path: str, is_segmented: Optional[bool] = None):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.is_segmented = is_segmented
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    @Slot()
    def run(self) -> None:
        global _ACTIVE_WORKERS
        with _ACTIVE_LOCK:
            _ACTIVE_WORKERS += 1

        try:
            if self._is_cancelled:
                return

            # Delegate to orchestrator; orchestrator must remain thread-safe.
            result = self.manager.audit_file(self.file_path, is_segmented=self.is_segmented)

            if not self._is_cancelled:
                self.signals.result.emit(result)

        except Exception:
            err_msg = traceback.format_exc()
            logger.error(f"Analysis Worker Failure: {err_msg}")
            self.signals.error.emit(err_msg)

        finally:
            with _ACTIVE_LOCK:
                _ACTIVE_WORKERS -= 1
            self.signals.finished.emit()


def get_threadpool_utilization(pool: QThreadPool) -> dict:
    """Returns monitored threadpool utilization stats."""
    try:
        max_threads = int(pool.maxThreadCount())
    except Exception:
        max_threads = 0
    with _ACTIVE_LOCK:
        active = int(_ACTIVE_WORKERS)
    return {"active": active, "max": max_threads}
