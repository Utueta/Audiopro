#!/bin/bash

"""
Audiopro v0.3.1
Handles the documentation of system threading, data flow, and industrial standards.
"""

# Low-level NVIDIA-SMI wrapper for real-time telemetry validation.
INTERVAL=1
LOG_FILE="logs/system.log" 

echo "--- Audiopro GPU/VRAM Monitor v0.3.1 ---"
watch -n $INTERVAL "nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
