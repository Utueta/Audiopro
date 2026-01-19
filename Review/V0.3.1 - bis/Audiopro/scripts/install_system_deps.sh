#!/bin/bash

"""
Audiopro OS Dependency Installer v0.3.1
- Role: Automated provisioning of non-Python system binaries.
- Targets: Debian/Ubuntu, Fedora, Arch, and macOS (Homebrew).
- Logic: Installs libmagic for security and ffmpeg for DSP decoding.
"""

echo "--- Audiopro Industrial Suite: Installing System Dependencies ---"

# Detect Operating System
OS="$(uname -s)"

# Check for sudo availability
if [ "$EUID" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
else
    SUDO=""
fi

case "${OS}" in
    Linux*)
        if [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
            echo "[System] Detected Debian/Ubuntu based system."
            $SUDO apt update
            # libmagic1: Security Gate | libsndfile1: Audio I/O | ffmpeg: Decoding
            $SUDO apt install -y libmagic1 libsndfile1 ffmpeg nvidia-smi || echo "Warning: Some packages failed to install."
            
        elif [ -f /etc/fedora-release ]; then
            echo "[System] Detected Fedora based system."
            $SUDO dnf install -y file-devel libsndfile ffmpeg-free nvidia-settings
            
        elif [ -f /etc/arch-release ]; then
            echo "[System] Detected Arch Linux based system."
            $SUDO pacman -Syu --noconfirm file libsndfile ffmpeg nvidia-utils
            
        else
            echo "[Error] Unsupported Linux distribution. Please install libmagic and ffmpeg manually."
            exit 1
        fi
        ;;
    Darwin*)
        echo "[System] Detected macOS. Using Homebrew."
        if ! command -v brew &> /dev/null; then
            echo "[Error] Homebrew not found. Please install it first at https://brew.sh/"
            exit 1
        fi
        brew install libmagic libsndfile ffmpeg
        ;;
    CYGWIN*|MINGW32*|MSYS*|MINGW*)
        echo "[System] Detected Windows environment."
        echo "[Note] libmagic is handled via python-magic-bin in requirements.txt."
        echo "[Note] Please ensure ffmpeg is installed and added to your PATH manually."
        ;;
    *)
        echo "[Error] Unknown OS: ${OS}"
        exit 1
        ;;
esac

echo "--- System dependencies installed successfully. ---"
echo "You may now run: pip install -r requirements.txt"
