#"""
#Audiopro v0.3.1
#Handles the global Application Constructor, Dependency Injection, and Signal Routing.
#- Orchestrates the initialization of Core, Persistence, and Service layers.
#- Logic: Injects LLM Arbitration (Ollama/Mock) into SystemManager.
#"""

import sys
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication

# 1. Domain & Infrastructure Imports
from core.logging_config import setup_logging
from core.manager import SystemManager
from core.analyzer.pipeline import AudioAnalysisPipeline
from core.brain.random_forest import AudioBrain
from persistence.repository import AnalysisResultStore
from services.ollama_llm import OllamaBridge
from ui.view import AudioproDashboard
from ui.splash_screen import AudioproSplashScreen

def bootstrap():
    # A. Initialize Telemetry (Forensic Logging)
    setup_logging()
    
    app = QApplication(sys.argv)
    
    # B. Launch Diagnostic Gatekeeper (Splash Screen)
    splash = AudioproSplashScreen()
    splash.show()
    
    # Run pre-flight health checks (Ollama/GPU/Weights)
    if not splash.run_diagnostics():
        sys.exit(1)

    # C. Dependency Injection Layer
    try:
        # Load Configuration
        with open("config.json", "r") as f:
            config = json.load(f)

        # Initialize Hexagonal Layers
        repository = AnalysisResultStore(config['paths']['db_path'])
        brain = AudioBrain(config['paths']['weights_path'])
        pipeline = AudioAnalysisPipeline()
        llm_service = OllamaBridge(config['llm']['endpoint'])
        
        # Core Orchestrator
        manager = SystemManager(
            pipeline=pipeline,
            brain=brain,
            repository=repository,
            llm_service=llm_service
        )

        # D. Dashboard Handoff
        dashboard = AudioproDashboard(manager)
        
        splash.finish(dashboard)
        dashboard.show()
        
        return app.exec()

    except Exception as e:
        import logging
        logging.getLogger("system").critical(f"BOOT_FAILURE: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(bootstrap())
