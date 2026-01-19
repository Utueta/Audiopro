#!/bin/bash
#"""
#Audiopro Deployment Orchestrator v0.3.1
#- Handles the automated directory structure creation and file migration.
#- Logic: Strictly follows structure.txt to implement Hexagonal Architecture.
#"""

PROJECT_NAME="Audiopro"

echo "--- Audiopro v0.3.1: Starting Deployment Orchestration ---"

# 1. Create Directory Hierarchy based on structure.txt
echo "[1/4] Provisioning industrial directory tree..."
mkdir -p "$PROJECT_NAME/core/analyzer"
mkdir -p "$PROJECT_NAME/core/brain/weights"
mkdir -p "$PROJECT_NAME/persistence"
mkdir -p "$PROJECT_NAME/services"
mkdir -p "$PROJECT_NAME/ui/components"
mkdir -p "$PROJECT_NAME/database"
mkdir -p "$PROJECT_NAME/logs"
mkdir -p "$PROJECT_NAME/assets/icons"
mkdir -p "$PROJECT_NAME/tests/fixtures"
mkdir -p "$PROJECT_NAME/scripts"
mkdir -p "$PROJECT_NAME/docs"

# 2. Migrate Root Files to Architecturally Correct Locations
echo "[2/4] Executing file migration logic..."

# Root Level
mv app.py config.json requirements.txt .gitignore ARCHITECTURE.md "$PROJECT_NAME/" 2>/dev/null

# Core Domain Layer
mv models.py workers.py manager.py "$PROJECT_NAME/core/" 2>/dev/null
mv pipeline.py dsp.py spectral.py metadata.py "$PROJECT_NAME/core/analyzer/" 2>/dev/null
mv random_forest.py model_interface.py "$PROJECT_NAME/core/brain/" 2>/dev/null

# Infrastructure Layer (Persistence & Services)
mv repository.py schema.py "$PROJECT_NAME/persistence/" 2>/dev/null
mv llm_interface.py ollama_llm.py mock_llm.py "$PROJECT_NAME/services/" 2>/dev/null

# Presentation Layer (UI)
mv view.py splash_screen.py theme.qss "$PROJECT_NAME/ui/" 2>/dev/null
mv mini_player.py gauges.py graphs.py "$PROJECT_NAME/ui/components/" 2>/dev/null

# DevOps & Maintenance
mv install_system_deps.sh retrain_model.py check_health.py smi.sh "$PROJECT_NAME/scripts/" 2>/dev/null

# 3. Initialize Python Package Markers
echo "[3/4] Initializing __init__.py markers for cross-layer imports..."
find "$PROJECT_NAME" -type d -not -path "*/.*" -exec touch {}/__init__.py \;

# 4. Post-Deployment Calibration
echo "[4/4] Triggering Sentinel Brain calibration..."
if [ -f "$PROJECT_NAME/scripts/init_model.py" ]; then
    cd "$PROJECT_NAME" && python3 scripts/init_model.py
else
    # Fallback if init_model was in root
    mv init_model.py "$PROJECT_NAME/scripts/" 2>/dev/null
    cd "$PROJECT_NAME" && python3 scripts/init_model.py
fi

echo "--- Deployment Complete. Industrial structure is now active. ---"
