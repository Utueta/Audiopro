#!/bin/bash

echo "⚠️  ALERTE : Réinitialisation de l'intelligence Audio Expert Pro V0.1..."
echo "------------------------------------------------------------------"

# 1. Arrêter proprement si l'app tourne (optionnel selon ton OS)
# pkill -f app.py

# 2. Suppression des fichiers de mémoire
if [ -f "audio_expert_v01.db" ]; then
    rm audio_expert_v01.db
    echo "✅ Base de données SQLite supprimée."
fi

if [ -f "audio_expert_rf.joblib" ]; then
    rm audio_expert_rf.joblib
    echo "✅ Modèle Machine Learning supprimé."
fi

# 3. Nettoyage des dossiers temporaires
if [ -d "logs" ]; then
    rm -rf logs/*
    echo "✅ Logs nettoyés."
fi

echo "------------------------------------------------------------------"
echo "🚀 Terminé. Au prochain lancement, l'IA sera totalement neuve."
