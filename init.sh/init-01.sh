#!/bin/bash

# Project Root Name
PROJECT_NAME="Audiopro"
COPIED_FILES=()

echo "-------------------------------------------------------"
echo "Industrial System Setup: $PROJECT_NAME (v0.2.5 Compliant)"
echo "-------------------------------------------------------"

# 1. Define the directory array based on the v0.2.5 manifest
directories=(
    "$PROJECT_NAME/core/analyzer"
    "$PROJECT_NAME/core/brain/weights"
    "$PROJECT_NAME/services"
    "$PROJECT_NAME/persistence"
    "$PROJECT_NAME/ui/components"
    "$PROJECT_NAME/database"
    "$PROJECT_NAME/logs"
    "$PROJECT_NAME/assets/icons"
    "$PROJECT_NAME/scripts"
    "$PROJECT_NAME/docs"
)

# Create missing subfolders
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "[+] Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# 2. Create __init__.py for Python package recognition
python_packages=(
    "$PROJECT_NAME/core"
    "$PROJECT_NAME/core/analyzer"
    "$PROJECT_NAME/core/brain"
    "$PROJECT_NAME/services"
    "$PROJECT_NAME/persistence"
    "$PROJECT_NAME/ui"
    "$PROJECT_NAME/ui/components"
)

for pkg in "${python_packages[@]}"; do
    touch "$pkg/__init__.py"
done

# 3. Synchronize Files to New Structure
echo "[+] Migrating project files..."

# Root Level
for file in app.py logging_config.py requirements.txt README.md; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/" && COPIED_FILES+=("$file")
done

# Core Logic
for file in manager.py workers.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/core/" && COPIED_FILES+=("core/$file")
done

# Analyzer Subsystem
for file in pipeline.py dsp.py spectral.py metadata.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/core/analyzer/" && COPIED_FILES+=("core/analyzer/$file")
done

# Brain Subsystem
for file in random_forest.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/core/brain/" && COPIED_FILES+=("core/brain/$file")
done

# Services (AI Providers)
for file in llm_interface.py ollama_llm.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/services/" && COPIED_FILES+=("services/$file")
done

# Persistence (Database)
for file in repository.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/persistence/" && COPIED_FILES+=("persistence/$file")
done

# UI & Components
for file in view.py styles.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/ui/" && COPIED_FILES+=("ui/$file")
done
[ -f "gauges.py" ] && cp "gauges.py" "$PROJECT_NAME/ui/components/" && COPIED_FILES+=("ui/components/gauges.py")

# Scripts & Maintenance
for file in init_model.py test_engine.py; do
    [ -f "$file" ] && cp "$file" "$PROJECT_NAME/scripts/" && COPIED_FILES+=("scripts/$file")
done

echo "-------------------------------------------------------"
echo "Migration Complete: ${#COPIED_FILES[@]} files synchronized."
echo "Target: ./$PROJECT_NAME"
echo "-------------------------------------------------------"
