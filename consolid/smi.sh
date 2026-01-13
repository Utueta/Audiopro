#!/bin/bash
# AUDIOPRO MONITORING & DEPLOYMENT TOOL (smi.sh)
# Version Consolidée - DevSecOps

echo -e "\e[1;34m[AUDIOPRO]\e[0m Lancement du monitoring système..."

# Vérification des dépendances système critiques pour Fedora
check_system_deps() {
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "\e[1;31m[ERREUR]\e[0m FFmpeg non trouvé. Installation suggérée : sudo dnf install ffmpeg"
    fi
    
    if ! command -v nvidia-smi &> /dev/null; then
        echo -e "\e[1;33m[WARN]\e[0m Drivers NVIDIA non détectés. Le ML tournera sur CPU."
    fi
}

# Fonction de monitoring hybride
monitor_resources() {
    # On utilise watch pour nvidia-smi tout en affichant les processus audiopro
    watch -n 1 "
    echo '--- GPU STATUS ---';
    nvidia-smi --query-gpu=timestamp,name,utilization.gpu,utilization.memory,temperature.gpu --format=csv,noheader;
    echo -e '\n--- CPU & RAM (AUDIOPRO) ---';
    ps -C python3 -o %cpu,%mem,cmd | grep 'app.py' || echo 'App.py non lancé';
    "
}

check_system_deps
monitor_resources
