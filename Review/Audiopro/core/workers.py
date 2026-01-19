"""
Audiopro Qt Infrastructure v0.2.6
- Updated with NVIDIA NVML for real-time telemetry
- Provides data for IndustrialGauge components
"""

import time
import logging
import pynvml  # Requires: pip install pynvml
from PySide6.QtCore import QObject, Signal, QRunnable, Slot

system_logger = logging.getLogger("system")

# --- SIGNALS ---

class WorkerSignals(QObject):
    result = Signal(object)
    telemetry = Signal(dict)   # Dictionary containing: gpu_util, vram_used, vram_total
    error = Signal(str)
    finished = Signal()

# --- WORKERS ---

class HardwareMonitorWorker(QRunnable):
    """
    Industrial Telemetry Polling.
    Uses NVML to communicate with NVIDIA drivers.
    """
    def __init__(self, poll_rate=0.5):
        super().__init__()
        self.poll_rate = poll_rate
        self.signals = WorkerSignals()
        self.is_running = True
        
        # Initialize NVML once upon worker creation
        try:
            pynvml.nvmlInit()
            self.handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Monitor primary GPU
        except Exception as e:
            system_logger.error(f"NVML Initialization Failed: {e}")
            self.is_running = False

    @Slot()
    def run(self):
        """Looping telemetry emission."""
        while self.is_running:
            try:
                # 1. Fetch GPU Utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(self.handle)
                gpu_load = util.gpu

                # 2. Fetch VRAM Metrics
                mem = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
                vram_used = mem.used / 1024 / 1024  # Convert bytes to MB
                vram_total = mem.total / 1024 / 1024

                # 3. Emit Telemetry Contract
                self.signals.telemetry.emit({
                    "gpu_util": gpu_load,
                    "vram_used": vram_used,
                    "vram_total": vram_total
                })

                time.sleep(self.poll_rate)

            except Exception as e:
                system_logger.critical(f"Telemetry Poll Failure: {e}")
                self.signals.error.emit("Hardware Telemetry Offline")
                break
        
        # Cleanup on exit
        try:
            pynvml.nvmlShutdown()
        except:
            pass
