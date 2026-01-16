# 🚀 Audio Expert Pro V0.2.2 - Obsidian Edition

**Audio Expert Pro** est une suite logicielle industrielle dédiée à l'analyse de l'intégrité audio et à la détection de fraudes spectrales (**Fake HQ / Upscaling**). 

Cette version **V0.2.2** marque une transition majeure vers une architecture hybride SQL/JSON, offrant une stabilité accrue et une interface "Obsidian" optimisée pour les environnements de studio.

---

## 🏗️ Architecture du Projet

Le projet suit une séparation stricte des préoccupations (SOC) pour garantir qu'aucune mise à jour du code ne vienne corrompre vos données d'apprentissage.

* **Logiciel (Code) :** `app.py`, `analyzer.py`, `model.py`, `view.py`, `llm_service.py`.
* **Intelligence :** Dossier `/models` (Cerveau Random Forest).
* **Données :** Dossier `/database` (Archive SQL + Cache JSON Rapide).
* **Maintenance :** Dossier `/scripts` (Automatisation système).



---

## ⚡ Installation Rapide

### 1. Prérequis
* **Ollama** : Pour l'arbitrage par IA (`ollama run qwen2.5`).
* **FFmpeg** : Backend indispensable pour le décodage audio.
* **NVIDIA GPU** : Pour le monitoring de charge en temps réel.

### 2. Installation Automatisée (Linux)
Le script détecte votre distribution (Debian, Ubuntu, Fedora, Arch) et installe les bibliothèques système nécessaires pour le son et l'interface graphique (Qt6).

```bash
chmod +x scripts/install_deps.sh
./scripts/install_deps.sh
