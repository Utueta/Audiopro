#!/bin/bash

# ==============================================================================
# INSTALLATEUR AUDIOPRO EXPERT - CONSOLIDÉ (FEDORA)
# Objectif : Robustesse, Respect des Codecs & Performance ML
# ==============================================================================

set -e 

# Couleurs pour le terminal
BLUE='\033[1;34m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}-------------------------------------------------------${NC}"
echo -e "${BLUE}🔍 AUDIOPRO : Audit de l'environnement système...${NC}"
echo -e "${BLUE}-------------------------------------------------------${NC}"

# 1. Protection Intelligente de FFmpeg
# On vérifie la présence du binaire et de sa provenance RPM
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VER=$(ffmpeg -version | head -n 1)
    echo -e "${GREEN}✅ FFmpeg détecté : $FFMPEG_VER${NC}"
    echo "Le script préserve votre version actuelle pour la stabilité des codecs."
    FFMPEG_PKG=""
else
    echo -e "📦 FFmpeg absent, préparation de l'installation de ffmpeg-free..."
    FFMPEG_PKG="ffmpeg-free"
fi

# 2. Installation des dépendances système (Sans écrasement)
echo -e "${BLUE}📦 Installation des dépendances système (DNF)...${NC}"
sudo dnf install -y \
    python3-pip \
    python3-devel \
    libsndfile \
    $FFMPEG_PKG \
    gcc \
    gcc-c++ \
    mesa-libGL \
    libxkbcommon-x11 \
    curl \
    sqlite \
    --skip-broken --best

# 3. Stack IA : Ollama & Arbitre Qwen 2.5
echo -e "${BLUE}🤖 Configuration de l'arbitre IA (Ollama)...${NC}"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama est déjà installé."
fi

# Activation du service
sudo systemctl enable --now ollama || true

echo "🧬 Chargement du modèle Qwen 2.5 (Audit & Arbitrage)..."
# Pull asynchrone pour ne pas bloquer si déjà présent
ollama pull qwen2.5

# 4. Pipeline Python & Précision Mathématique
echo -e "${BLUE}🐍 Installation de la stack Python consolidée...${NC}"
python3 -m pip install --user --upgrade pip

# Installation basée sur les requirements consolidés précédemment
# On utilise --user pour éviter les conflits système sur Fedora
pip install --user --upgrade \
    PySide6>=6.5.0 \
    librosa==0.10.1 \
    numpy>=1.24.0 \
    scikit-learn>=1.3.0 \
    scipy>=1.10.0 \
    matplotlib>=3.8.0 \
    requests>=2.31.0 \
    joblib>=1.3.0 \
    psutil>=5.9.0 \
    pandas>=2.0.0

# 5. Scaffolding & Intégrité (Vérification des répertoires)
echo -e "${BLUE}📂 Organisation des répertoires de certification...${NC}"
mkdir -p logs database models assets

# Exécution du setup projet si présent
if [ -f "setup_project.py" ]; then
    python3 setup_project.py
fi

echo -e "${BLUE}-------------------------------------------------------${NC}"
echo -e "${GREEN}✅ INSTALLATION TERMINÉE AVEC SUCCÈS${NC}"
echo -e "🎨 Style : Obsidian Glow (Activé)"
echo -e "🧠 Brain : Qwen 2.5 & Random Forest (Prêts)"
echo -e "🚀 Lancez l'application : ${BLUE}python3 app.py${NC}"
echo -e "${BLUE}-------------------------------------------------------${NC}"
