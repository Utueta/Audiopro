import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool

# Import Architecture Layers
from persistence.repository import AudioRepository
from core.manager import AnalysisManager
from ui.view import MainWindow

def setup_logging():
    """Configures segregated logging as per ARCHITECTURE.md."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler("logs/system.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    # 1. Initialize the Application
    app = QApplication(sys.argv)
    setup_logging()
    logger = logging.getLogger("Audiopro.Boot")
    logger.info("Initializing Audiopro Industrial System...")

    try:
        # 2. Infrastructure Layer: Global Thread Pool
        thread_pool = QThreadPool.globalInstance()
        
        # Reserved: Keep 1 core free for UI responsiveness
        max_threads = max(1, thread_pool.maxThreadCount() - 1)
        thread_pool.setMaxThreadCount(max_threads)
        logger.info(f"Thread pool initialized with {max_threads} workers.")

        # 3. Persistence Layer: SQLite Repository (WAL Mode)
        repository = AudioRepository("database/audiopro_v01.db")
        logger.info("Persistence layer connected (WAL Mode active).")

        # 4. Application Layer: The Orchestrator (Dependency Injection)
        manager = AnalysisManager(thread_pool, repository)

        # 5. Presentation Layer: Main Window
        window = MainWindow(manager)
        window.show()

        # 6. Execution Loop
        exit_code = app.exec()
        
        logger.info("Shutting down Audiopro system gracefully.")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"System startup failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
