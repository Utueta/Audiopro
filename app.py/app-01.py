"""
Audiopro Bootloader v0.2.5
- Initializes Hexagon Core and Presentation Layer
- Performs Dependency Injection for Repository, Brain, and LLM
- Executes the Qt Event Loop
"""

import sys
import logging
import logging_config
from PySide6.QtWidgets import QApplication

# Infrastructure Imports
from persistence.repository import Repository
from core.brain.random_forest import AudioBrain
from services.ollama_llm import OllamaLLM
from core.manager import Manager
from ui.view import MainView


logging_config.setup_logging()
# Setup Global Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bootloader")

def bootstrap():
    """
    Initializes components and wires signals/slots.
    """
    app = QApplication(sys.argv)
    
    # 1. Instantiate Infrastructure (Data & Intelligence)
    try:
        repo = Repository("database/audiopro_v01.db")
        brain = AudioBrain(weights_dir="core/brain/weights")
        llm_service = OllamaLLM(host="http://localhost:11434")
        
        # 2. Instantiate Orchestrator (Domain Logic)
        manager = Manager(repository=repo, brain=brain, llm_service=llm_service)
        
        # 3. Instantiate View (Presentation)
        view = MainView()
        
        # 4. Wire Signals: UI -> Manager
        # Using the Industrial View's 'request_analysis' signal
        view.request_analysis.connect(manager.start_analysis)
        
        # 5. Wire Signals: Manager -> UI
        manager.analysis_completed.connect(view.update_results_table)
        manager.telemetry_received.connect(view.update_telemetry)
        manager.status_updated.connect(lambda msg: view.status_bar.showMessage(msg, 3000))
        
        # 6. Initialize Hardware Monitoring (Example: 1Hz poll)
        # In production, connect a real NVML/PSUTIL function here
        # manager.start_hardware_monitoring(telemetry_func=get_hardware_stats)

        logger.info("Audiopro v0.2.5 System Online.")
        view.show()
        sys.exit(app.exec())

    except Exception as e:
        logger.critical(f"System Boot Failure: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    bootstrap()
