#!/bin/bash

# ==============================================================================
# INSTALLATEUR AUDIO EXPERT PRO - CIBLE FEDORA LINUX
# Gère : Système, Audio DSP, ML, Ollama (IA) & Modèles
# ==============================================================================

set -e # Interruption immédiate en cas d'erreur

echo "-------------------------------------------------------"
echo "🔍 Initialisation de l'installation Expert Pro"
echo "-------------------------------------------------------"

# 1. Mise à jour des dépôts et installation des outils de base
echo "📦 [1/5] Mise à jour des paquets système DNF..."
sudo dnf update -y
sudo dnf install -y \
    python3-pip \
    python3-devel \
    libsndfile \
    ffmpeg-free \
    gcc \
    gcc-c++ \
    mesa-libGL \
    libxkbcommon-x11 \
    curl \
    sqlite

# 2. Installation et Configuration de l'IA (Ollama)
echo "🤖 [2/5] Configuration du moteur IA Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "📥 Téléchargement et installation d'Ollama via script officiel..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama est déjà installé."
fi

echo "⚙️  Activation du service Ollama (systemd)..."
sudo systemctl daemon-reload
sudo systemctl enable --now ollama

# 3. Récupération du modèle Qwen (L'Arbitre)
echo "🧬 [3/5] Pull du modèle Qwen 2.5 (peut prendre quelques minutes)..."
# On s'assure que le service a démarré avant de pull
sleep 3
ollama pull qwen2.5

# 4. Préparation de la Stack Python & Machine Learning
echo "🐍 [4/5] Installation des dépendances Python (Pip)..."
# Mise à jour de pip pour éviter les problèmes de roue (wheels)
python3 -m pip install --user --upgrade pip

# Installation groupée pour optimiser la résolution de dépendances
pip install --user \
    PySide6 \
    librosa \
    numpy \
    scikit-learn \
    matplotlib \
    mutagen \
    psutil \
    joblib \
    soundfile \
    requests

# 5. Lancement de l'organisation des fichiers (Scaffolding)
echo "📂 [5/5] Structuration de l'arborescence du projet..."
if [ -f "setup_project.py" ]; then
    python3 setup_project.py
elif [ -f "scripts/setup_project.py" ]; then
    python3 scripts/setup_project.py
else
    echo "⚠️  setup_project.py non trouvé. L'arborescence ne sera pas modifiée."
fi

echo "-------------------------------------------------------"
echo "✅ INSTALLATION TERMINÉE AVEC SUCCÈS"
echo "-------------------------------------------------------"
echo "Résumé de l'environnement :"
echo " - IA : Ollama + Qwen 2.5 (Actif)"
echo " - ML : Scikit-Learn (Prêt)"
echo " - Audio : Libsndfile + FFmpeg (Configuré)"
echo ""
echo "🚀 Pour démarrer l'application : python3 app.py"
echo "-------------------------------------------------------"
