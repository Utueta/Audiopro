#!/bin/bash
PROJECT_DIR="AudioExpert_Pro"
SOURCE="install.rs"

echo "💎 DÉPLOIEMENT AUDIO EXPERT PRO"

# 1. Extraction (Logique script ancien)
mkdir -p "$PROJECT_DIR"
current_file=""
while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ $line == FILE:* ]]; then
        current_file=$(echo "$line" | cut -d':' -f2)
        mkdir -p "$PROJECT_DIR/$(dirname "$current_file")"
        > "$PROJECT_DIR/$current_file"
    elif [[ $line == "---" ]]; then
        current_file=""
    elif [[ -n $current_file ]]; then
        echo "$line" >> "$PROJECT_DIR/$current_file"
    fi
done < "$SOURCE"

# 2. Finalisation structure (Logique script nouveau)
cd "$PROJECT_DIR"
touch __init__.py
touch services/__init__.py

# 3. Installation (Fix Python 3.13)
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install PySide6 librosa "numpy<2.0.0" scipy scikit-learn joblib requests mutagen

# 4. Initialisation modèle
python3 init_model.py

echo "✅ Prêt ! 'source venv/bin/activate && python3 app.py'"
