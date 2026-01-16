#!/bin/bash
# Script d'installation des dépendances pour l'Analyseur Audio V2

echo "Identification de la distribution..."
if [ -f /etc/debian_version ]; then
    # Ubuntu, Debian, Mint, Kali, etc.
    echo "Distribution détectée : Debian/Ubuntu"
    sudo apt update
    sudo apt install -y python3-pip python3-dev libsndfile1 ffmpeg portaudio19-dev
elif [ -f /etc/fedora-release ]; then
    # Fedora
    echo "Distribution détectée : Fedora"
    sudo dnf install -y python3-pip python3-devel libsndfile ffmpeg-free portaudio-devel
elif [ -f /etc/arch-release ]; then
    # Arch Linux, Manjaro
    echo "Distribution détectée : Arch Linux"
    sudo pacman -Syu --needed python-pip libsndfile ffmpeg portaudio
else
    echo "Distribution non reconnue officiellement. Tentative via pip uniquement."
fi

echo "Installation des bibliothèques Python..."
pip install --upgrade pip
pip install librosa soundfile numpy scipy requests pygame mutagen scikit-learn
