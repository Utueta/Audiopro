"""
Audiopro v0.3.1
Handles the management of system-level and analysis-level industrial logging.
"""
import logging
import logging.handlers
from pathlib import Path

def setup_logging():
    """
    Industrial Logging Setup:
    - Renames audit.log to analysis.log (v0.3.1 Architecture Compliance)
    - Implements high-detail DSP telemetry routing
    """
    # 1. Ensure Logs Directory Exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 2. Define Formatter (Industrial Standard)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. System Logger: Infrastructure & UI Events
    sys_handler = logging.handlers.RotatingFileHandler(
        "logs/system.log", maxBytes=5*1024*1024, backupCount=3
    )
    sys_handler.setFormatter(formatter)
    
    system_logger = logging.getLogger("system")
    system_logger.setLevel(logging.INFO)
    system_logger.addHandler(sys_handler)

    # 4. Analysis Logger: DSP Metrics & ML Verdicts (Audit Trail)
    # REGRESSION FIX: Updated path to logs/analysis.log per ARCHITECTURE.md
    analysis_handler = logging.handlers.RotatingFileHandler(
        "logs/analysis.log", maxBytes=10*1024*1024, backupCount=10
    )
    analysis_handler.setFormatter(formatter)
    
    analysis_logger = logging.getLogger("analysis")
    analysis_logger.setLevel(logging.DEBUG) 
    analysis_logger.addHandler(analysis_handler)

    # 5. Console Output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)
