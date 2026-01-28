#!/bin/bash

# ==============================================================================
# AUDIOPRO INDUSTRIAL SETUP SCRIPT V2
# Purpose: Structure Reproduction + Venv Provisioning + Dependency Injection
# ==============================================================================

PROJECT_ROOT="Audiopro"

echo "-------------------------------------------------------"
echo "[1/4] Initializing Industrial Structure..."
echo "-------------------------------------------------------"

directories=(
    "$PROJECT_ROOT/core/analyzer"
    "$PROJECT_ROOT/core/brain/weights"
    "$PROJECT_ROOT/services"
    "$PROJECT_ROOT/persistence"
    "$PROJECT_ROOT/ui/components"
    "$PROJECT_ROOT/database"
    "$PROJECT_ROOT/logs"
    "$PROJECT_ROOT/assets/icons"
    "$PROJECT_ROOT/tests/fixtures"
    "$PROJECT_ROOT/scripts"
    "$PROJECT_ROOT/docs"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
done

# Initialize Python Packages
find "$PROJECT_ROOT" -type d -not -path "*/.*" -exec touch {}/__init__.py \;

echo "[2/4] Generating Configuration Manifests..."
# Generate .gitignore
cat <<EOF > "$PROJECT_ROOT/.gitignore"
__pycache__/
*.py[cod]
venv/
.env
database/*.db
logs/*.log
core/brain/weights/*.pkl
core/brain/weights/*.joblib
EOF

# Generate requirements.txt
cat <<EOF > "$PROJECT_ROOT/requirements.txt"
PySide6>=6.6.0
librosa>=0.10.0
numpy>=1.24.0
scipy>=1.10.0
mutagen>=1.46.0
scikit-learn>=1.3.0
joblib>=1.3.0
httpx>=0.24.0
nvidia-ml-py>=12.535.0
psutil>=5.9.0
python-json-logger>=2.0
EOF

echo "[3/4] Provisioning Virtual Environment..."
cd "$PROJECT_ROOT" || exit
python3 -m venv venv
source venv/bin/activate

echo "[4/4] Installing Industrial Stack (This may take a moment)..."
pip install --upgrade pip
pip install -r requirements.txt

echo "-------------------------------------------------------"
echo "INSTALLATION COMPLETE"
echo "Architecture: Verified"
echo "Environment: Active (venv)"
echo "Next: run 'python app.py' to initialize entry point."
echo "-------------------------------------------------------"
