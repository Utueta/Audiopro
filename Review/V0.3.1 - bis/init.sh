#!/bin/bash
"""
Audiopro init.sh v0.3.1
- Handles the documentation triage.
- Role: Automated project skeleton provisioning for Hexagonal Architecture.
- Logic: Creates all domain, infrastructure, and presentation layers.
"""

PROJECT_NAME="Audiopro"

echo "--- Audiopro v0.3.1: Initializing Project Structure ---"

# 1. Define Directory Tree based on structure.txt
directories=(
    "$PROJECT_NAME/core/analyzer"
    "$PROJECT_NAME/core/brain/weights"
    "$PROJECT_NAME/persistence"
    "$PROJECT_NAME/services"
    "$PROJECT_NAME/ui/components"
    "$PROJECT_NAME/database"
    "$PROJECT_NAME/logs"
    "$PROJECT_NAME/assets/icons"
    "$PROJECT_NAME/tests/fixtures"
    "$PROJECT_NAME/scripts"
    "$PROJECT_NAME/docs"
)

# 2. Create Directories
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "[Created] $dir"
    else
        echo "[Exists]  $dir"
    fi
done

# 3. Initialize Python Packages (Required for cross-layer imports)
echo "--- Provisioning __init__.py markers ---"
find "$PROJECT_NAME" -type d -not -path "*/.*" -exec touch {}/__init__.py \;

# 4. Permissions check
chmod +x "$PROJECT_NAME/scripts/"*.sh 2>/dev/null

echo "--- Initialization Complete. You can now run the Deployment Orchestrator. ---"
