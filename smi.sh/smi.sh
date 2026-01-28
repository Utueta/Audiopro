#!/bin/bash

# Audiopro Industrial Resource Monitor v0.2.5
# Low-level NVIDIA-SMI wrapper for real-time telemetry validation.

# 1. Configuration
INTERVAL=1  # Refresh rate in seconds
LOG_FILE="logs/system.log" # For infrastructure trace alignment 

echo "--------------------------------------------------------"
echo " Audiopro GPU/VRAM Monitor (SMI-Lite) "
echo "--------------------------------------------------------"
echo "Monitoring NVIDIA Hardware... Press [CTRL+C] to exit."

# 2. Execution Loop
# This mirrors the HardwareMonitorWorker logic in a shell environment 
watch -n $INTERVAL "nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"

# 3. Error Handling
if [ $? -ne 0 ]; then
    echo "[!] Error: nvidia-smi not found or CUDA driver not responding."
    echo "[!] Logged to $LOG_FILE"
    exit 1
fi
