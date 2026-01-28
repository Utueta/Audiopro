import psutil
import os
import logging
from PySide6.QtCore import QObject, Signal, QTimer

class TelemetrySystem(QObject):
    """
    Industrial-grade telemetry for real-time resource tracking.
    Monitors CPU, RAM, I/O, and SQLite WAL growth[cite: 37, 40, 41].
    """
    resource_alert = Signal(str, str)  # Level, Message
    metrics_updated = Signal(dict)

    def __init__(self, db_path, config):
        super().__init__()
        self.db_path = db_path
        self.wal_path = f"{db_path}-wal"
        self.config = config
        self.logger = logging.getLogger("system")
        
        # Periodic monitoring timer (e.g., every 2 seconds)
        self.timer = QTimer()
        self.timer.timeout.connect(self.collect_metrics)
        self.timer.start(2000)

    def collect_metrics(self):
        # 1. CPU & RAM Tracking [cite: 40]
        cpu_usage = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        
        # 2. Disk I/O Monitoring [cite: 41]
        io_counters = psutil.disk_io_counters()
        
        # 3. SQLite WAL Growth Monitoring 
        wal_size_mb = 0
        if os.path.exists(self.wal_path):
            wal_size_mb = os.path.getsize(self.wal_path) / (1024 * 1024)

        metrics = {
            "cpu_percent": cpu_usage,
            "ram_percent": ram.percent,
            "wal_size_mb": wal_size_mb,
            "io_read": io_counters.read_bytes,
            "io_write": io_counters.write_bytes
        }

        self.metrics_updated.emit(metrics)
        self._check_thresholds(metrics)

    def _check_thresholds(self, metrics):
        # Global Saturation Alerts [cite: 40]
        if metrics["ram_percent"] > 85:
            self.resource_alert.emit("WARNING", "RAM saturation above 85%")
            
        # WAL Growth Alert 
        # Threshold defined in config.json, default 512MB
        wal_threshold = self.config.get("wal_limit_mb", 512)
        if metrics["wal_size_mb"] > wal_threshold:
            self.logger.warning(f"WAL file growth exceeds threshold: {metrics['wal_size_mb']:.2f}MB")
            self.resource_alert.emit("CRITICAL", "SQLite WAL growth alert: Disk bloating risk")
