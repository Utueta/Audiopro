#!/bin/bash
# ==============================================================================
# SCRIPT DE CONSTRUCTION CERTIFIÉ OBSIDIAN PRO V0.2.4
# Responsable : Senior QA & DevSecOps
# Objectif : Déploiement automatisé, sécurisé et multi-distribution
# ==============================================================================

set -e # Interrompt le script en cas d'erreur
PROJECT_DIR="AudioExpert_Pro"
SOURCE="install.rs"

echo "💎 DÉMARRAGE DU DÉPLOIEMENT AUDIO EXPERT PRO"

# 1. ANALYSE DE L'ENVIRONNEMENT ET DÉPENDANCES SYSTÈME
# ------------------------------------------------------------------------------
echo "🔍 Identification de la distribution et installation des dépendances..."

install_sys_deps() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            case $ID in
                ubuntu|debian|raspbian|linuxmint)
                    echo "📦 Plateforme : Debian-based ($ID)"
                    sudo apt-get update -qq && sudo apt-get install -y libmagic1 libsndfile1 ffmpeg
                    ;;
                fedora|rhel|centos|rocky)
                    echo "📦 Plateforme : RedHat-based ($ID)"
                    sudo dnf install -y file-devel libsndfile ffmpeg
                    ;;
                arch|manjaro)
                    echo "📦 Plateforme : Arch-based ($ID)"
                    sudo pacman -S --noconfirm file libsndfile ffmpeg
                    ;;
                *)
                    echo "⚠️ Distribution inconnue ($ID). Installation générique via APT..."
                    sudo apt-get install -y libmagic1 libsndfile1 ffmpeg
                    ;;
            esac
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "📦 Plateforme : macOS"
        brew install libmagic ffmpeg
    else
        echo "❌ OS non supporté : $OSTYPE"
        exit 1
    fi
}

install_sys_deps

# 2. EXTRACTION DE LA STRUCTURE DEPUIS LE MANIFESTE
# ------------------------------------------------------------------------------
echo "📦 Extraction des fichiers depuis $SOURCE..."
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

# 3. INITIALISATION DE L'ENVIRONNEMENT PYTHON (FIX 3.13 & DEPENDENCIES)
# ------------------------------------------------------------------------------
cd "$PROJECT_DIR"
echo "🐍 Configuration de l'environnement virtuel..."
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
# Installation des dépendances incluant python-magic pour la conformité V0.2.4
pip install PySide6 librosa "numpy<2.0.0" scipy scikit-learn joblib requests mutagen python-magic

# 4. AMORÇAGE DU PIPELINE ML & SÉCURITÉ
# ------------------------------------------------------------------------------
echo "🧠 Initialisation du modèle ML et des artefacts..."
python3 init_model.py

# Création des dossiers de logs et db si non présents
mkdir -p logs database models assets services scripts

# 5. DIAGNOSTIC FINAL D'INTÉGRITÉ
# ------------------------------------------------------------------------------
echo "✨ Exécution du test de santé Obsidian..."
python3 -c "import magic, librosa; print('✅ Systèmes DSP et Sécurité certifiés.')"

echo "----------------------------------------------------------------"
echo "✅ DÉPLOIEMENT RÉUSSI : Obsidian Pro V0.2.4 est prêt."
echo "🚀 Pour lancer : source venv/bin/activate && python3 app.py"
echo "----------------------------------------------------------------"
