"""
core/workers.py - Thread-safe Qt workers for asynchronous file analysis.

SCOPE:
- Threading boilerplate (QRunnable management)
- Signal emission with Qt.QueuedConnection enforcement
- Cancellation token support for graceful shutdown

CRITICAL CONSTRAINTS (ARCHITECTURE.md §2):
- Workers NEVER access ui/ components directly
- All signals use Qt.QueuedConnection for thread-safe delivery
- Data passed as immutable objects from core/models.py
- Thread affinity verified in debug builds

OUT OF SCOPE:
- Business logic (delegated to manager)
- UI updates (handled by signal receivers on main thread)
- Data validation (manager's responsibility)
"""

from PySide6.QtCore import QRunnable, QObject, Signal, Qt
import traceback
import logging
from typing import Callable, Optional, Dict, Any
from pathlib import Path
from threading import Event


logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """
    Thread-safe signal bridge between worker threads and Qt main thread.
    
    CRITICAL (ARCHITECTURE.md §2):
    Qt automatically routes these signals to the main thread via event queue
    when connected with Qt.QueuedConnection (enforced in UI layer).
    
    Thread Affinity:
    - WorkerSignals created on main thread
    - Signals emitted from worker thread
    - Qt queues emission to main thread event loop
    - Slot execution guaranteed on main thread
    
    Signals:
        result: Emitted on successful analysis with immutable result dict
        error: Emitted on failure with error message string
        progress: Emitted during analysis with percentage (0-100)
        cancelled: Emitted when analysis cancelled by user/shutdown
        finished: Always emitted on completion (success/failure/cancellation)
    """
    result = Signal(dict)       # Success: analysis result (immutable)
    error = Signal(str)         # Failure: user-facing error message
    progress = Signal(int)      # Optional: progress percentage (0-100)
    cancelled = Signal()        # Cancellation: user or shutdown initiated
    finished = Signal()         # Completion: always emitted


class AnalysisWorker(QRunnable):
    """
    QRunnable for asynchronous audio file analysis.
    
    CRITICAL CONSTRAINTS (ARCHITECTURE.md §2 - Worker Pattern):
    1. NEVER access UI components in run()
    2. All UI updates via signals with Qt.QueuedConnection only
    3. func must be thread-safe (manager handles internal locking)
    4. No shared mutable state between workers
    5. Data passed as immutable objects from core/models.py
    6. Each worker gets own SQLite connection via repository factory
    
    Thread Affinity:
    - Constructor called on main thread
    - run() executes on QThreadPool worker thread
    - Signals automatically queued to main thread (when Qt.QueuedConnection used)
    - Qt deletes worker after run() completes (setAutoDelete=True)
    
    Cancellation Support (ARCHITECTURE.md §2 - Cancellation Tokens):
    - Workers check cancellation_token periodically
    - Manager can cancel workers during shutdown or user stop
    - Cancelled workers emit cancelled signal and exit gracefully
    
    Example Usage (with explicit Qt.QueuedConnection):
        cancellation_token = Event()
        worker = AnalysisWorker(
            file_path="/path/to/audio.wav",
            func=manager.process_new_file,
            cancellation_token=cancellation_token
        )
        # CRITICAL: Use Qt.QueuedConnection for thread safety
        worker.signals.result.connect(
            ui.on_success, 
            Qt.ConnectionType.QueuedConnection  # REQUIRED
        )
        worker.signals.error.connect(
            ui.on_error, 
            Qt.ConnectionType.QueuedConnection
        )
        worker.signals.cancelled.connect(
            ui.on_cancelled, 
            Qt.ConnectionType.QueuedConnection
        )
        worker.signals.finished.connect(
            ui.on_complete, 
            Qt.ConnectionType.QueuedConnection
        )
        QThreadPool.globalInstance().start(worker)
        
        # To cancel (ARCHITECTURE.md §2 - Cancellation):
        cancellation_token.set()
    """
    
    def __init__(
        self,
        file_path: str,
        func: Callable[[str, Optional[Event]], Optional[Dict[str, Any]]],
        cancellation_token: Optional[Event] = None
    ):
        """
        Initialize worker with analysis target and function.
        
        Args:
            file_path: Path to audio file to analyze
            func: Thread-safe analysis function
                  Signature: func(file_path: str, cancel_token: Optional[Event]) -> Optional[dict]
                  Must check cancel_token.is_set() periodically
                  Must return immutable dict (from core/models.py)
            cancellation_token: Optional Event for cancellation support
        
        Note:
            func returning None indicates deduplication (analysis already in progress).
            This is NOT an error - it's a valid optimization.
        
        Thread Affinity:
            Constructor called on main thread.
            WorkerSignals inherits main thread affinity.
        """
        super().__init__()
        self.file_path = file_path
        self.func = func
        self.signals = WorkerSignals()
        self.cancellation_token = cancellation_token or Event()
        
        # CRITICAL: Qt automatically deletes worker after run() completes
        # Without this, workers accumulate in memory (leak)
        self.setAutoDelete(True)
        
        logger.debug(f"Worker created for: {file_path}")
    
    def run(self):
        """
        Execute analysis on worker thread.
        
        CRITICAL (ARCHITECTURE.md §2 - Explicit Thread Affinity):
        Never call UI methods here - use signals instead.
        This method runs on a QThreadPool worker thread, NOT the main thread.
        
        Flow:
        1. Check cancellation before starting
        2. Call manager function (thread-safe, returns immutable dict)
        3. Emit result signal on success (queued to main thread)
        4. Emit error signal on failure (queued to main thread)
        5. Emit cancelled signal if stopped (queued to main thread)
        6. Always emit finished signal (in finally block)
        
        Thread Safety:
        - All signals queued to main thread via Qt event loop
        - No direct UI access
        - Result dict is immutable (from core/models.py)
        """
        logger.info(f"Worker started: {self.file_path}")
        
        # Early cancellation check (ARCHITECTURE.md §2 - Cancellation Tokens)
        if self.cancellation_token.is_set():
            logger.info(f"Worker cancelled before start: {self.file_path}")
            self.signals.cancelled.emit()
            self.signals.finished.emit()
            return
        
        try:
            # Delegate to manager (must be thread-safe)
            # Pass cancellation token so manager can check during long operations
            # Returns immutable dict from core/models.py
            result = self.func(self.file_path, self.cancellation_token)
            
            # Check cancellation after function return
            if self.cancellation_token.is_set():
                logger.info(f"Worker cancelled during execution: {self.file_path}")
                self.signals.cancelled.emit()
                return
            
            # Handle None result (deduplication optimization)
            if result is None:
                logger.info(f"Deduplication: analysis already in progress for {self.file_path}")
                self.signals.error.emit(
                    f"Analysis already in progress: {Path(self.file_path).name}"
                )
                return
            
            # Success: emit result (queued to main thread via Qt.QueuedConnection)
            logger.info(f"Worker succeeded: {self.file_path}")
            self.signals.result.emit(result)
        
        # User errors (file system issues)
        except FileNotFoundError:
            if not self.cancellation_token.is_set():
                error_msg = f"File not found: {Path(self.file_path).name}"
                logger.warning(error_msg)
                self.signals.error.emit(error_msg)
        
        except PermissionError:
            if not self.cancellation_token.is_set():
                error_msg = f"Permission denied: {Path(self.file_path).name}"
                logger.warning(error_msg)
                self.signals.error.emit(error_msg)
        
        except IsADirectoryError:
            if not self.cancellation_token.is_set():
                error_msg = f"Expected file, got directory: {Path(self.file_path).name}"
                logger.warning(error_msg)
                self.signals.error.emit(error_msg)
        
        # System errors (unexpected failures)
        except Exception as e:
            if not self.cancellation_token.is_set():
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
            else:
                logger.info(f"Worker cancelled with exception: {self.file_path}")
                self.signals.cancelled.emit()
        
        finally:
            # CRITICAL: Always signal completion (success or failure)
            # UI relies on this to reset state (hide progress, enable buttons, etc.)
            logger.debug(f"Worker finished: {self.file_path}")
            self.signals.finished.emit()
