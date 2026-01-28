#!/bin/bash

# Couleurs pour le terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}--- 🚀 Préparation de l'environnement Audio Expert V0.1 ---${NC}"

# 1. Détection et installation selon la distribution
if [ -f /etc/debian_version ]; then
    echo -e "${GREEN}Distribution : Debian/Ubuntu${NC}"
    sudo apt update
    # Ajout des libs GUI (libxcb, libegl) et codecs
    sudo apt install -y python3-pip libsndfile1 ffmpeg libxcb-cursor0 libegl1 libopengl0
elif [ -f /etc/fedora-release ]; then
    echo -e "${GREEN}Distribution : Fedora${NC}"
    sudo dnf install -y python3-pip libsndfile ffmpeg
elif [ -f /etc/arch-release ]; then
    echo -e "${GREEN}Distribution : Arch Linux${NC}"
    sudo pacman -Syu --needed python-pip libsndfile ffmpeg
else
    echo -e "${YELLOW}Distribution inconnue. Installation manuelle requise : ffmpeg, libsndfile, python-pip${NC}"
fi

# 2. Vérification critique : Nvidia-SMI (Spécification VRAM V0.1)
echo -e "${BLUE}--- 🔍 Vérification du support GPU ---${NC}"
if command -v nvidia-smi &> /dev/null
then
    echo -e "${GREEN}✅ Nvidia-SMI détecté. Le monitoring VRAM sera actif.${NC}"
else
    echo -e "${YELLOW}⚠️ nvidia-smi non trouvé. Le monitoring GPU sera désactivé dans l'interface.${NC}"
fi

# 3. Installation des dépendances Python (Audit d'intégrité)
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}--- 🐍 Installation des bibliothèques Python ---${NC}"
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo -e "${YELLOW}⚠️ requirements.txt non trouvé. Pensez à l'exécuter plus tard.${NC}"
fi

echo -e "${GREEN}✅ Installation terminée. Prêt pour V0.1.${NC}"
