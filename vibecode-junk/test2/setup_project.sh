#!/bin/bash
PROJECT_DIR="AudioExpert_V024"
SOURCE="install.rs"

echo "💎 AUDIO EXPERT PRO - DÉPLOIEMENT ULTIME"

# 1. Extraction des fichiers (Logique du script "Ancien")
echo "📋 Extraction depuis $SOURCE..."
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

# 2. Correction structure Python (Ajout des __init__.py)
cd "$PROJECT_DIR"
touch __init__.py
touch services/__init__.py

# 3. Installation robuste (Logique du script "Nouveau")
echo "🐍 Configuration environnement (Fix Python 3.13)..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
# On installe les versions compatibles avec votre système
pip install PySide6 librosa "numpy<2.0.0" scipy scikit-learn joblib requests mutagen --quiet

# 4. Amorçage
python3 init_model.py

echo "✅ TERMINÉ ! Lancez l'application avec :"
echo "   cd $PROJECT_DIR && source venv/bin/activate && python3 app.py"
