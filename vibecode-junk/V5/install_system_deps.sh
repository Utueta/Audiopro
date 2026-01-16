#!/bin/bash

# Couleurs pour le terminal
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}--- Installation des dépendances système (Audio Expert V4) ---${NC}"

if [ -f /etc/debian_version ]; then
    echo "Distribution détectée : Debian/Ubuntu"
    sudo apt update
    sudo apt install -y python3-pip libsndfile1 ffmpeg
elif [ -f /etc/fedora-release ]; then
    echo "Distribution détectée : Fedora"
    sudo dnf install -y python3-pip libsndfile ffmpeg
elif [ -f /etc/arch-release ]; then
    echo "Distribution détectée : Arch Linux"
    sudo pacman -Syu --needed python-pip libsndfile ffmpeg
else
    echo "Distribution inconnue. Assurez-vous d'avoir ffmpeg et libsndfile installés."
fi

echo -e "${GREEN}Installation système terminée.${NC}"
