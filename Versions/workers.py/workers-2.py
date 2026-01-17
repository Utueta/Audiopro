"""
core/workers.py - Thread-safe Qt workers for asynchronous file analysis.

SCOPE:
- Threading boilerplate (QRunnable management)
- Signal emission (result, error, progress, finished)
- Exception handling and error propagation

OUT OF SCOPE:
- Business logic (delegated to manager)
- UI updates (handled by signal receivers)
- Data validation (manager's responsibility)
"""

from PySide6.QtCore import QRunnable, QObject, Signal
import traceback
import logging
from typing import Callable, Optional, Dict, Any
from pathlib import Path


logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """
    Thread-safe signal bridge between worker threads and Qt main thread.
    
    Qt automatically routes these signals to the main thread via event queue,
    ensuring UI updates happen on the correct thread.
    
    Signals:
        result: Emitted on successful analysis with result dict
        error: Emitted on failure with error message string
        progress: Emitted during analysis with percentage (0-100)
        finished: Always emitted on completion (success or failure)
    """
    result = Signal(dict)       # Success: analysis result
    error = Signal(str)         # Failure: user-facing error message
    progress = Signal(int)      # Optional: progress percentage (0-100)
    finished = Signal()         # Completion: always emitted (success or failure)


class AnalysisWorker(QRunnable):
    """
    QRunnable for asynchronous audio file analysis.
    
    CRITICAL CONSTRAINTS (enforced by architecture):
    1. Never access UI components in run()
    2. All UI updates via signals only
    3. func must be thread-safe (manager handles internal locking)
    4. No shared mutable state between workers
    
    Thread Affinity:
    - run() executes on QThreadPool worker thread
    - Signals automatically queued to main thread
    - Qt deletes worker after run() completes (setAutoDelete=True)
    
    Example Usage:
        worker = AnalysisWorker(
            file_path="/path/to/audio.wav",
            func=manager.process_new_file
        )
        worker.signals.result.connect(ui.on_success, Qt.QueuedConnection)
        worker.signals.error.connect(ui.on_error, Qt.QueuedConnection)
        worker.signals.finished.connect(ui.on_complete, Qt.QueuedConnection)
        QThreadPool.globalInstance().start(worker)
    """
    
    def __init__(self, file_path: str, func: Callable[[str], Optional[Dict[str, Any]]]):
        """
        Initialize worker with analysis target and function.
        
        Args:
            file_path: Path to audio file to analyze
            func: Thread-safe analysis function (must accept file_path, return dict or None)
                  Typically manager.process_new_file
        
        Note:
            func returning None indicates deduplication (analysis already in progress).
            This is NOT an error - it's a valid optimization.
        """
        super().__init__()
        self.file_path = file_path
        self.func = func
        self.signals = WorkerSignals()
        
        # CRITICAL: Qt automatically deletes worker after run() completes
        # Without this, workers accumulate in memory (leak)
        self.setAutoDelete(True)
        
        logger.debug(f"Worker created for: {file_path}")
    
    def run(self):
        """
        Execute analysis on worker thread.
        
        CRITICAL: Never call UI methods here - use signals instead.
        This method runs on a QThreadPool worker thread, NOT the main thread.
        
        Flow:
        1. Call manager function (thread-safe)
        2. Emit result signal on success
        3. Emit error signal on failure
        4. Always emit finished signal (in finally block)
        """
        logger.info(f"Worker started: {self.file_path}")
        
        try:
            # Delegate to manager (must be thread-safe)
            result = self.func(self.file_path)
            
            # Handle None result (deduplication optimization)
            if result is None:
                logger.info(f"Deduplication: analysis already in progress for {self.file_path}")
                self.signals.error.emit(
                    f"Analysis already in progress: {Path(self.file_path).name}"
                )
                return
            
            # Success: emit result (queued to main thread)
            logger.info(f"Worker succeeded: {self.file_path}")
            self.signals.result.emit(result)
        
        # User errors (file system issues)
        except FileNotFoundError:
            error_msg = f"File not found: {Path(self.file_path).name}"
            logger.warning(error_msg)
            self.signals.error.emit(error_msg)
        
        except PermissionError:
            error_msg = f"Permission denied: {Path(self.file_path).name}"
            logger.warning(error_msg)
            self.signals.error.emit(error_msg)
        
        except IsADirectoryError:
            error_msg = f"Expected file, got directory: {Path(self.file_path).name}"
            logger.warning(error_msg)
            self.signals.error.emit(error_msg)
        
        # System errors (unexpected failures)
        except Exception as e:
            # Detailed error for debugging (includes traceback)
            error_msg = (
                f"Analysis failed: {Path(self.file_path).name}\n"
                f"Error: {type(e).__name__}: {str(e)}\n"
                f"Traceback:\n{traceback.format_exc()}"
            )
            logger.error(error_msg)
            
            # User-facing error (simplified)
            user_error = f"Analysis failed: {Path(self.file_path).name}\n{type(e).__name__}: {str(e)}"
            self.signals.error.emit(user_error)
        
        finally:
            # CRITICAL: Always signal completion (success or failure)
            # UI relies on this to reset state (hide progress, enable buttons, etc.)
            logger.debug(f"Worker finished: {self.file_path}")
            self.signals.finished.emit()


# Optional: Worker with progress reporting capability
class ProgressiveAnalysisWorker(AnalysisWorker):
    """
    Extended worker with progress reporting.
    
    Use this if your analysis function supports progress callbacks.
    Otherwise, use standard AnalysisWorker.
    
    Example:
        def analyze_with_progress(file_path, progress_callback):
            progress_callback(10)  # Loading
            # ... DSP analysis ...
            progress_callback(50)  # ML inference
            # ... classification ...
            progress_callback(90)  # Saving
            return result
        
        worker = ProgressiveAnalysisWorker(
            file_path=path,
            func=lambda p: analyze_with_progress(p, worker.report_progress)
        )
    """
    
    def report_progress(self, percentage: int):
        """
        Report progress from analysis function.
        
        Args:
            percentage: Progress percentage (0-100)
        
        Note:
            This is called FROM the analysis function, not by the worker.
            The analysis function must accept a progress callback.
        """
        if 0 <= percentage <= 100:
            self.signals.progress.emit(percentage)
        else:
            logger.warning(f"Invalid progress value: {percentage} (must be 0-100)")
