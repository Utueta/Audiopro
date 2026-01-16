#!/bin/bash

PROJECT_DIR="AudioExpert_Pro_V024"
SOURCE="install.rs"

echo "💎 AUDIO EXPERT PRO - DÉPLOIEMENT V0.2.4"
echo "------------------------------------------------------"

# 1. Validation de la source
if [ ! -f "$SOURCE" ]; then
    echo "❌ Erreur : $SOURCE introuvable."
    exit 1
fi

# 2. Création de la structure Obsidian (Axe C Ready)
echo "📂 Création de l'arborescence..."
mkdir -p "$PROJECT_DIR/services"
mkdir -p "$PROJECT_DIR/database"
mkdir -p "$PROJECT_DIR/models"
mkdir -p "$PROJECT_DIR/logs"

# 3. Extraction chirurgicale
echo "📋 Extraction des composants..."
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

# 4. Environnement et Initialisation (Axe B Ready)
echo "🐍 Configuration de l'environnement virtuel..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "🧠 Pré-entraînement du modèle initial..."
python init_model.py

echo "------------------------------------------------------"
echo "✅ SYSTÈME PRÊT"
echo "Commandes : cd $PROJECT_DIR && source venv/bin/activate && python app.py"
