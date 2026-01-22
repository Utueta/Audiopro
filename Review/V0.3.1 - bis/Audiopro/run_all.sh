#!/bin/bash
#"""
#Audiopro run_all.sh v0.3.1
#- Handles the full system orchestration.
#- Role: Sequence bootloader (Health -> Calibration -> App).
#"""

echo "--- Audiopro v0.3.1 Industrial Suite: Master Launch Sequence ---"

# 1. System Health Check
echo "[1/3] Running Infrastructure Diagnostics..."
python3 scripts/check_health.py
if [ $? -ne 0 ]; then
    echo "ERROR: System health check failed. Ensure Ollama and CUDA are ready."
    exit 1
fi

# 2. Intelligence Calibration
echo "[2/3] Verifying Sentinel Brain Artifacts..."
if [ ! -f "core/brain/weights/random_forest.pkl" ] || [ ! -f "core/brain/weights/scaler_v0.3.pkl" ]; then
    echo "Missing artifacts. Triggering initial calibration..."
    python3 scripts/init_model.py
fi

# 3. Application Execution
echo "[3/3] Launching Obsidian Pro Dashboard..."
python3 app.py
