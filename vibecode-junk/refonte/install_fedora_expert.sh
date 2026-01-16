#!/bin/bash

# ==============================================================================
# INSTALLATEUR AUDIO EXPERT PRO - FEDORA (PROTECTION DES CODECS)
# Version : 2.8 - Ne remplace JAMAIS FFmpeg si déjà présent
# ==============================================================================

set -e 

echo "-------------------------------------------------------"
echo "🔍 Vérification des composants déjà installés..."
echo "-------------------------------------------------------"

# 1. Identification intelligente de FFmpeg
# On vérifie si ffmpeg (version complète) ou ffmpeg-free est déjà là
if rpm -q ffmpeg &> /dev/null || rpm -q ffmpeg-free &> /dev/null; then
    echo "✅ FFmpeg est déjà présent. Le script ne touchera pas à vos codecs."
    FFMPEG_TO_INSTALL=""
else
    echo "📦 FFmpeg absent, préparation de l'installation de ffmpeg-free..."
    FFMPEG_TO_INSTALL="ffmpeg-free"
fi

# 2. Installation des dépendances sans forcer de remplacement
echo "📦 Installation des bibliothèques système manquantes..."
# On retire --allowerasing pour être CERTAIN de ne rien supprimer
# On ajoute --nosignature si vous avez des dépôts tiers qui bloquent
sudo dnf install -y \
    python3-pip \
    python3-devel \
    libsndfile \
    $FFMPEG_TO_INSTALL \
    gcc \
    gcc-c++ \
    mesa-libGL \
    libxkbcommon-x11 \
    curl \
    sqlite \
    --skip-broken --best

# 3. IA : Ollama & Modèle Qwen 2.5
echo "🤖 Configuration d'Ollama et de l'arbitre Qwen..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

sudo systemctl daemon-reload
sudo systemctl enable --now ollama || sudo systemctl start ollama

echo "🧬 Récupération du modèle Qwen 2.5 (Skip si déjà présent)..."
sleep 5
ollama pull qwen2.5

# 4. Stack Python & ML
echo "🐍 Installation des modules Python..."
python3 -m pip install --user --upgrade pip

# On installe/met à jour les libs Python
pip install --user --upgrade \
    PySide6 librosa numpy scikit-learn \
    matplotlib mutagen psutil joblib \
    soundfile requests

# 5. Scaffolding
echo "📂 Organisation des fichiers..."
[ -f "setup_project.py" ] && python3 setup_project.py
[ -f "scripts/setup_project.py" ] && python3 scripts/setup_project.py

echo "-------------------------------------------------------"
echo "✅ TERMINÉ : Votre version de FFmpeg a été préservée."
echo "🚀 Lancez l'expert avec : python3 app.py"
echo "-------------------------------------------------------"
