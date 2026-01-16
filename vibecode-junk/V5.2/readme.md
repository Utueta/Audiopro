# 🚀 Audio Expert Pro V0.1

**Audio Expert Pro** est une station de travail intelligente dédiée à l'analyse, la qualification et le nettoyage de bibliothèques audio massives. Alliant traitement de signal traditionnel, Machine Learning et arbitrage par IA locale, cette version **V0.1** offre une précision chirurgicale pour débusquer les fichiers corrompus et les fraudes de qualité (Fake HQ).

---

## 🔬 Spécifications Techniques

### 1. Moteur d'Analyse Avancé (`analyzer.py`)
Le cœur du système évalue chaque fichier sur 5 piliers physiques :
* **SNR (Signal-to-Noise Ratio)** : Mesure la pureté du signal par rapport au bruit de fond.
* **Clipping** : Détection de la saturation numérique et de la distorsion d'amplitude.
* **Crackling** : Identification des craquements et artefacts impulsionnels.
* **Phase** : Vérification de la corrélation stéréo (inversion ou mono forcé).
* **Fake HQ (Upscaling)** : Identification des coupures spectrales suspectes (ex: 16kHz).

### 2. Intelligence & Apprentissage (`model.py`)
* **Random Forest Regressor** : Une IA qui apprend de vos décisions pour affiner le score de suspicion.
* **Mémoire SQLite** : Historique intégral, métadonnées (Mutagen) et empreintes **Blake2b** pour une détection de doublons infaillible.

### 3. Monitoring & Performance (`view.py` & `app.py`)
* **Surveillance VRAM (Nvidia-SMI)** : VU-mètres temps réel intégrés pour surveiller la charge GPU et la mémoire vidéo.
* **Pipeline Asynchrone** : Scan multi-cœurs via `QThreadPool` pour maintenir une interface fluide.
* **Double Visualisation** : Waveform et Spectrogramme dynamiques via Matplotlib.

---

## 🤖 Arbitrage IA & LLM
Le système est pré-configuré pour communiquer avec **Ollama (Qwen 2.5)**. Pour les fichiers en "zone grise" (incertitude statistique), l'IA locale fournit un verdict textuel détaillé expliquant la nature du défaut détecté. Ce processus est entièrement local et garantit la confidentialité de vos données.

---

## 🛠 Installation Simplifiée (All-in-One)

La version **V0.1** introduit un processus d'installation automatisé. Le script système gère désormais l'intégralité des dépendances (Codecs, Bibliothèques GUI, Pilotes et Paquets Python).

### 🚀 Procédure unique
1.  Ouvrez un terminal dans le dossier du projet.
2.  Lancez le script maître :
    ```bash
    chmod +x install_system_deps.sh
    ./install_system_deps.sh
    ```

**Ce que fait ce script :**
* **Système** : Installe `ffmpeg`, `libsndfile` et les dépendances Qt (`libxcb`, `libegl`).
* **Matériel** : Vérifie la présence de `nvidia-smi` pour le monitoring GPU.
* **Python** : Met à jour `pip` et installe automatiquement toutes les librairies listées dans `requirements.txt`.

---

## 🌟 Avantages Clés
* **Fiabilité Scientifique** : Élimine les fraudes audio invisibles à l'oreille.
* **Productivité** : Traitement de plusieurs To de données en temps record.
* **Autonomie Totale** : Analyse ML et LLM 100% locale (sans abonnement).
* **Monitoring Matériel** : Visualisez l'état de votre GPU directement depuis l'application.

---

## 📂 Organisation du Projet
* `app.py` : Orchestrateur et gestionnaire de threads.
* `view.py` : Interface utilisateur et monitoring GPU.
* `analyzer.py` : Algorithmes de traitement de signal.
* `model.py` : Base de données et Machine Learning.
* `config.json` : Seuils et configuration IA.
* `requirements.txt` : Liste des modules Python.

---
**Version 0.1** - *L'excellence technique au service de la préservation audio.*
