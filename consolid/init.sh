#!/bin/bash

# Project Root Name
PROJECT_NAME="Audiopro"
COPIED_FILES=()

echo "-------------------------------------------------------"
echo "Industrial System Setup: $PROJECT_NAME"
echo "-------------------------------------------------------"

# Define the directory array based on the architectural manifest
directories=(
    "$PROJECT_NAME/core/analyzer"
    "$PROJECT_NAME/core/brain/weights"
    "$PROJECT_NAME/services"
    "$PROJECT_NAME/persistence"
    "$PROJECT_NAME/ui/components"
    "$PROJECT_NAME/database"
    "$PROJECT_NAME/logs"
    "$PROJECT_NAME/assets/icons"
    "$PROJECT_NAME/tests/fixtures"
    "$PROJECT_NAME/scripts"
    "$PROJECT_NAME/docs"
)

# Loop to create missing subfolders
for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "[+] Creating missing directory: $dir"
        mkdir -p "$dir"
    else
        echo "[.] Directory already exists: $dir"
    fi
done

# Create essential __init__.py files for Python package recognition
python_packages=(
    "$PROJECT_NAME/core"
    "$PROJECT_NAME/core/analyzer"
    "$PROJECT_NAME/core/brain"
    "$PROJECT_NAME/services"
    "$PROJECT_NAME/persistence"
    "$PROJECT_NAME/ui"
    "$PROJECT_NAME/ui/components"
    "$PROJECT_NAME/tests"
)

for pkg in "${python_packages[@]}"; do
    touch "$pkg/__init__.py"
done

# Copy project files to the new structure
echo "[+] Copying project files to $PROJECT_NAME structure..."

# Root files
for file in app.py config.json requirements.txt .gitignore; do
    if [ -f "$file" ]; then
        cp "$file" "$PROJECT_NAME/"
        COPIED_FILES+=("$file")
    fi
done

# Core files
for file in models.py workers.py manager.py; do
    if [ -f "$file" ]; then
        cp "$file" "$PROJECT_NAME/core/"
        COPIED_FILES+=("core/$file")
    fi
done

# Analyzer files
for file in pipeline.py dsp.py spectral.py metadata.py; do
    if [ -f "analyzer/$file" ]; then
        cp "analyzer/$file" "$PROJECT_NAME/core/analyzer/"
        COPIED_FILES+=("core/analyzer/$file")
    fi
done

# Brain files
for file in model_interface.py random_forest.py; do
    if [ -f "brain/$file" ]; then
        cp "brain/$file" "$PROJECT_NAME/core/brain/"
        COPIED_FILES+=("core/brain/$file")
    fi
done

# Services files
for file in llm_interface.py ollama_llm.py mock_llm.py; do
    if [ -f "services/$file" ]; then
        cp "services/$file" "$PROJECT_NAME/services/"
        COPIED_FILES+=("services/$file")
    fi
done

# Persistence files
for file in repository.py schema.py; do
    if [ -f "persistence/$file" ]; then
        cp "persistence/$file" "$PROJECT_NAME/persistence/"
        COPIED_FILES+=("persistence/$file")
    fi
done

# UI files
for file in view.py splash_screen.py theme.qss; do
    if [ -f "ui/$file" ]; then
        cp "ui/$file" "$PROJECT_NAME/ui/"
        COPIED_FILES+=("ui/$file")
    fi
done

# UI components
for file in mini_player.py gauges.py graphs.py; do
    if [ -f "ui/components/$file" ]; then
        cp "ui/components/$file" "$PROJECT_NAME/ui/components/"
        COPIED_FILES+=("ui/components/$file")
    fi
done

# Tests files
for file in test_pipeline.py test_model.py test_llm_service.py test_repository.py; do
    if [ -f "tests/$file" ]; then
        cp "tests/$file" "$PROJECT_NAME/tests/"
        COPIED_FILES+=("tests/$file")
    fi
done

# Scripts files
for file in install_system_deps.sh init_model.py check_health.py smi.sh; do
    if [ -f "scripts/$file" ]; then
        cp "scripts/$file" "$PROJECT_NAME/scripts/"
        COPIED_FILES+=("scripts/$file")
    fi
done

# Docs files
for file in README.md TUTORIAL.md RELEASE_NOTES.md ARCHITECTURE.md certification_report.md; do
    if [ -f "docs/$file" ]; then
        cp "docs/$file" "$PROJECT_NAME/docs/"
        COPIED_FILES+=("docs/$file")
    fi
done

# Database and logs (if exist)
[ -f database/audiopro_v01.db ] && cp database/audiopro_v01.db "$PROJECT_NAME/database/" && COPIED_FILES+=("database/audiopro_v01.db")
[ -f logs/analysis.log ] && cp logs/analysis.log "$PROJECT_NAME/logs/" && COPIED_FILES+=("logs/analysis.log")
[ -f logs/system.log ] && cp logs/system.log "$PROJECT_NAME/logs/" && COPIED_FILES+=("logs/system.log")

# Assets
if [ -d assets/icons ]; then
    cp -r assets/icons/* "$PROJECT_NAME/assets/icons/"
    COPIED_FILES+=("assets/icons/*")
fi

# Test fixtures
if [ -d tests/fixtures ]; then
    cp -r tests/fixtures/* "$PROJECT_NAME/tests/fixtures/"
    COPIED_FILES+=("tests/fixtures/*")
fi

echo "-------------------------------------------------------"
echo "Structure Verified, Synchronized & Files Copied."
echo ""
echo "Summary of copied files:"
for file in "${COPIED_FILES[@]}"; do
    echo "  - $file"
done
echo ""
echo "Total files copied: ${#COPIED_FILES[@]}"
echo "-------------------------------------------------------"

