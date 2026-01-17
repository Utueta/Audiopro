import threading
import time
import logging

# Configuration of Logging (from V0.2.3)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - GAUGE - %(levelname)s - %(message)s')

class Gauge:
    """
    Consolidated Gauge implementation:
    - Thread-safe value updates (V0.2.2)
    - Threshold monitoring & alerts (V0.2.3)
    - Clean setter/getter API (V0.2.4)
    """
    def __init__(self, name, min_val=0, max_val=100, thresholds=None):
        self.name = name
        self.min_val = min_val
        self.max_val = max_val
        self._current_value = min_val
        self._lock = threading.Lock()
        
        # Thresholds: {'warning': 70, 'critical': 90}
        self.thresholds = thresholds or {'warning': 75, 'critical': 90}
        self.status = "OK"

    @property
    def value(self):
        with self._lock:
            return self._current_value

    @value.setter
    def value(self, new_val):
        # Constraints (V0.2.1)
        if new_val < self.min_val: new_val = self.min_val
        if new_val > self.max_val: new_val = self.max_val
        
        with self._lock:
            self._current_value = new_val
            self._check_status()

    def _check_status(self):
        """Internal monitoring logic (Consolidated V0.2.3)"""
        if self._current_value >= self.thresholds['critical']:
            if self.status != "CRITICAL":
                logging.error(f"[{self.name}] CRITICAL threshold reached: {self._current_value}")
                self.status = "CRITICAL"
        elif self._current_value >= self.thresholds['warning']:
            if self.status != "WARNING":
                logging.warning(f"[{self.name}] Warning threshold reached: {self._current_value}")
                self.status = "WARNING"
        else:
            self.status = "OK"

    def get_percent(self):
        """Mathematical logic for UI rendering (Inherited from V3-V5)"""
        return ((self.value - self.min_val) / (self.max_val - self.min_val)) * 100

    def __repr__(self):
        return f"<Gauge(name={self.name}, value={self.value}, status={self.status})>"

# Example of usage for the consolidated version
if __name__ == "__main__":
    cpu_gauge = Gauge("CPU_Usage", thresholds={'warning': 50, 'critical': 80})
    cpu_gauge.value = 55  # Triggers Warning Log
    cpu_gauge.value = 85  # Triggers Critical Log
    print(f"Current UI Level: {cpu_gauge.get_percent()}%")
