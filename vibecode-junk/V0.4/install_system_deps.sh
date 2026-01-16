#!/bin/bash

# --- Palette de Couleurs Obsidian ---
CYAN='\033[0;36m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}--- 🚀 Initialisation Audio Expert Pro V0.2.2 (Obsidian) ---${NC}"

# 1. Création de la structure de dossiers (Crucial pour la V0.2)
echo -e "${CYAN}📂 Configuration de l'arborescence...${NC}"
mkdir -p database models logs assets scripts
echo -e "${GREEN}✅ Structure des dossiers prête.${NC}"

# 2. Détection et installation des dépendances système (FFmpeg & Libs GUI)
if [ -f /etc/debian_version ]; then
    echo -e "${GREEN}Distribution : Debian/Ubuntu détectée${NC}"
    sudo apt update
    # libxcb-cursor0 et libegl1 sont critiques pour PySide6/Qt6
    sudo apt install -y python3-pip libsndfile1 ffmpeg libxcb-cursor0 libegl1 libopengl0 libxcb-xinerama0
elif [ -f /etc/fedora-release ]; then
    echo -e "${GREEN}Distribution : Fedora détectée${NC}"
    sudo dnf install -y python3-pip libsndfile ffmpeg libxcb
elif [ -f /etc/arch-release ]; then
    echo -e "${GREEN}Distribution : Arch Linux détectée${NC}"
    sudo pacman -Syu --needed python-pip libsndfile ffmpeg
else
    echo -e "${YELLOW}Distribution inconnue. Assurez-vous d'avoir installé : ffmpeg, libsndfile, et les libs XCB pour Qt.${NC}"
fi

# 3. Vérification critique : Nvidia-SMI (Monitoring VRAM Pro)
echo -e "${CYAN}🔍 Diagnostic Support GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✅ Nvidia-SMI détecté. Monitoring VRAM haute précision activé.${NC}"
else
    echo -e "${YELLOW}⚠️ nvidia-smi non trouvé. L'interface passera en mode CPU/RAM uniquement.${NC}"
fi

# 4. Installation des dépendances Python figées (Audit de conformité)
if [ -f "requirements.txt" ]; then
    echo -e "${CYAN}🐍 Installation du stack Python (V0.2.2 Stable)...${NC}"
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    echo -e "${GREEN}✅ Bibliothèques Python installées.${NC}"
else
    echo -e "${RED}❌ ERREUR : requirements.txt manquant. Impossible de finaliser l'audit.${NC}"
    exit 1
fi

# 5. Finalisation et Permissions
chmod +x scripts/*.sh 2>/dev/null
echo -e "${GREEN}--------------------------------------------------${NC}"
echo -e "${GREEN}✨ Installation terminée avec succès !${NC}"
echo -e "${BLUE}💡 Commande de lancement : ${NC}python3 app.py"
echo -e "${GREEN}--------------------------------------------------${NC}"
