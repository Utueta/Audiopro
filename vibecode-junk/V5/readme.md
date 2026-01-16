README - Audio Expert Pro V4.1
📋 Présentation

Station de travail audio intelligente permettant le scan massif de bibliothèques, l'analyse de signal (SNR, Clipping, Fake HQ) et l'arbitrage automatisé par Intelligence Artificielle locale (Ollama).
🛠️ Installation Rapide
1. Dépendances Système (Linux)
Bash

chmod +x install_system_deps.sh
./install_system_deps.sh

2. Dépendances Python
Bash

python3 install_python_deps.py

3. Configuration de l'IA

    Installer Ollama.

    Lancer le serveur : ollama serve.

    Télécharger le modèle : ollama pull qwen2.5:7b-instruct-q4_K_M.

⚙️ Paramétrage (config.json)

    clipping_threshold : 0.98 (seuil de détection de saturation).

    fake_hq_threshold_khz : 16.0 (les fichiers coupant avant 16kHz sont pénalisés).

    gray_zone : définit la plage de scores (ex: 40-70) envoyée au LLM pour arbitrage.

🚀 Utilisation

    Lancer l'application : python3 app.py.

    Cliquer sur "Sélectionner un dossier".

    Une fois le scan terminé, l'onglet "Résultats" affiche la liste triable par score.

    L'IA affiche son verdict dans le journal en bas de l'écran pour les fichiers ambigus.

    Dans l'onglet "Révision", sélectionnez un fichier pour voir sa waveform et son analyse spectrale détaillée.

⚠️ Sécurité & Maintenance

    Base de données : Le fichier audio_expert_v4.db peut être ouvert avec n'importe quel éditeur SQLite pour des rapports personnalisés.

    Logs : En cas de plantage, vérifiez analysis.log.

    Corbeille : L'option "Envoyer à la corbeille" utilise send2trash pour éviter toute perte définitive accidentelle.
