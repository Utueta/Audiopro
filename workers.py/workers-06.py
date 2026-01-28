import logging
import traceback
from pathlib import Path
from typing import Callable, Any, Dict, Optional
from PySide6.QtCore import QRunnable, QObject, Signal, Slot

logger = logging.getLogger("Audiopro.Worker")

class AnalysisSignals(QObject):
    """
    Thread-safe signal bridge for Industrial Audio Analysis.
    """
    progress = Signal(int)      # Progress percentage (0-100)
    dsp_ready = Signal(dict)    # Partial results after DSP phase
    result = Signal(dict)       # Final result (DSP + ML + LLM)
    error = Signal(str)         # Formatted error message with traceback
    finished = Signal()         # Completion notification

class AnalysisWorker(QRunnable):
    """
    Audiopro Random Forest Brain v0.2.5 - Analysis Worker
    
    Consolidated implementation handling the full pipeline:
    Metadata -> DSP -> ML Brain -> LLM Arbitrage.
    """
    def __init__(self, file_path: str, manager_func: Callable[[str], Dict[str, Any]]):
        super().__init__()
        self.file_path = file_path
        self.manager_func = manager_func
        self.signals = AnalysisSignals()
        
        # Guard: Ensure thread is reaped by QThreadPool to prevent memory leaks
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """
        Executes the analysis pipeline. Isolated from the Main UI thread.
        """
        try:
            logger.info(f"Starting analysis: {Path(self.file_path).name}")
            
            # Step 1: Execute Pipeline (Thread-safe call to CentralManager)
            # The manager handles the internal transition: 
            # Features (DSP) -> Scaler (Z-Score) -> Random Forest
            result = self.manager_func(self.file_path)
            
            if result is None:
                # Handle de-duplication if manager is already processing
                logger.info(f"File {self.file_path} is already being processed or skipped.")
                return

            # Step 2: Ensure path integrity for UI mapping
            result['path'] = self.file_path
            
            # Step 3: Emit final payload
            self.signals.result.emit(result)

        except Exception as e:
            # Phase 2 & 6 Requirement: Full Traceability
            error_details = (
                f"Analysis Failure: {Path(self.file_path).name}\n"
                f"Exception: {type(e).__name__}: {str(e)}\n"
                f"{traceback.format_exc()}"
            )
            logger.error(error_details)
            self.signals.error.emit(error_details)
            
        finally:
            self.signals.finished.emit()

    def report_progress(self, value: int):
        """Callback used by manager to update UI progress."""
        self.signals.progress.emit(value)
