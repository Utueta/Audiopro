from PySide6.QtCore import QObject, QThreadPool, Signal, Slot
from core.workers import AnalysisWorker
from core.analyzer.pipeline import AudioAnalyzer
from persistence.repository import AudioRepository
from core.models import AnalysisResult

class AnalysisManager(QObject):
    """The Hexagon Orchestrator: Connects UI to Core/Repo."""
    
    # Signal to notify UI that a new result is ready for rendering
    analysis_ready = Signal(AnalysisResult)

    def __init__(self, thread_pool: QThreadPool, repository: AudioRepository):
        super().__init__()
        self.thread_pool = thread_pool
        self.repository = repository
        self.analyzer = AudioAnalyzer()

    def request_analysis(self, file_path: str):
        """Public entry point for the non-blocking pipeline."""
        worker = AnalysisWorker(file_path, self.analyzer.analyze_file)
        
        # Connect internal workers to safe main-thread slots
        worker.signals.result.connect(self._on_result_received)
        
        self.thread_pool.start(worker)

    @Slot(AnalysisResult)
    def _on_result_received(self, result: AnalysisResult):
        """Main Thread handler for persistence and UI notification."""
        if result.success:
            # 1. Persist to DB (using the WAL-ready repository)
            self.repository.save_result(result)
            
            # 2. Notify UI components for live update
            self.analysis_ready.emit(result)
        else:
            # Traceability: Ensure failures are visible in the logs
            print(f"Manager received error: {result.error}")
