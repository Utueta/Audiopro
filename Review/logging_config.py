"""
Audiopro Industrial Logging v0.2.5
- Segmented log routing (System vs. Analysis)
- JSON-ready formatting for external audit tools
- Automatic log rotation to prevent disk saturation
"""

import logging
import logging.handlers
from pathlib import Path

def setup_logging():
    # 1. Ensure Logs Directory Exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 2. Define Formatter (Industrial Standard)
    # Format: Timestamp | Level | Component | Message
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-12s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. System Logger: Infrastructure, Database, and UI Events
    sys_handler = logging.handlers.RotatingFileHandler(
        "logs/system.log", maxBytes=5*1024*1024, backupCount=3
    )
    sys_handler.setFormatter(formatter)
    
    system_logger = logging.getLogger("system")
    system_logger.setLevel(logging.INFO)
    system_logger.addHandler(sys_handler)

    # 4. Analysis Logger: DSP Metrics, ML Verdicts, and LLM Arbitration
    # This is the "Audit Trail"
    audit_handler = logging.handlers.RotatingFileHandler(
        "logs/audit.log", maxBytes=10*1024*1024, backupCount=10
    )
    audit_handler.setFormatter(formatter)
    
    analysis_logger = logging.getLogger("analysis")
    analysis_logger.setLevel(logging.DEBUG) # Catch high-detail DSP telemetry
    analysis_logger.addHandler(audit_handler)

    # 5. Console Output (Cleaned for Developer)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Root logger directs to console
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().setLevel(logging.INFO)

    system_logger.info("Industrial Logging Subsystem Online.")
