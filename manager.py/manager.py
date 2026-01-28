"""
Audiopro Orchestrator v0.2.5
- Manages asynchronous worker lifecycles via QThreadPool
- Implements Conditional LLM Arbitration logic
- Connects DSP outputs to Persistence and UI layers
"""

import logging
from PySide6.QtCore import QObject, QThreadPool, Signal, Slot
from core.workers import AnalysisWorker, HardwareMonitorWorker
from core.analyzer.pipeline import run_pipeline
from core.models import AnalysisResult

system_logger = logging.getLogger("system")

class Manager(QObject):
    """
    The central hub for system operations.
    Coordinates threading, ML inference, and external service calls.
    """
    # Signals for the UI (view.py)
    analysis_completed = Signal(object)  # Emits final AnalysisResult
    status_updated = Signal(str)         # UI Status bar messages
    telemetry_received = Signal(dict)    # GPU/VRAM data

    def __init__(self, repository, brain, llm_service):
        super().__init__()
        self.repo = repository
        self.brain = brain
        self.llm = llm_service
        
        # Threading infrastructure
        self.thread_pool = QThreadPool.globalInstance()
        self.active_monitors = []

    def start_analysis(self, file_path: str):
        """
        Queues an audio file for asynchronous auditing.
        """
        worker = AnalysisWorker(
            file_path=file_path,
            pipeline_func=run_pipeline,
            brain_func=self.brain.classify
        )
        
        # Connect internal worker signals to manager orchestration
        worker.signals.result.connect(self._process_result)
        worker.signals.error.connect(lambda e: system_logger.error(f"Analysis Error: {e}"))
        
        self.thread_pool.start(worker)

    def start_hardware_monitoring(self, telemetry_func):
        """
        Initiates the background hardware telemetry loop.
        """
        monitor = HardwareMonitorWorker(telemetry_func=telemetry_func)
        monitor.signals.telemetry.connect(self.telemetry_received.emit)
        
        self.active_monitors.append(monitor)
        self.thread_pool.start(monitor)

    @Slot(object)
    def _process_result(self, result: AnalysisResult):
        """
        Logic Gate: Determines if LLM Arbitration is required.
        """
        final_result = result

        # Conditional LLM Arbitration
        # Triggered if ML Brain label is 'SUSPICIOUS' or confidence is low
        if result.ml_classification == "SUSPICIOUS":
            self.status_updated.emit(f"Arbitrating: {result.file_name}...")
            
            arbitration = self.llm.arbitrate(result.file_name, {
                "snr_value": result.snr_value,
                "clipping_count": result.clipping_count,
                "suspicion_score": result.suspicion_score
            })
            
            # Update the result with the LLM's final verdict
            final_result = AnalysisResult(
                file_hash=result.file_hash,
                file_name=result.file_name,
                file_path=result.file_path,
                snr_value=result.snr_value,
                clipping_count=result.clipping_count,
                suspicion_score=result.suspicion_score,
                ml_classification=arbitration.get("verdict", "CORRUPT"),
                ml_confidence=1.0  # LLM override is considered absolute
            )

        # Persistence: Save to SQLite via Repository
        self.repo.save_analysis(final_result)
        
        # UI Update
        self.analysis_completed.emit(final_result)
