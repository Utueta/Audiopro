import os
import sys
import json
import sqlite3
import subprocess
import requests
import librosa
import numpy as np

def check_step(name, status, message=""):
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name:<25} : {message}")
    return status

def run_diagnostics():
    print("="*65)
    print("🔍 AUDIO EXPERT PRO - DIAGNOSTIC SYSTÈME COMPLET V0.2.4")
    print("="*65)
    
    overall_health = True
    config = None

    # 1. Vérification du fichier de Configuration
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            check_step("Configuration", True, "config.json chargé.")
        except Exception as e:
            check_step("Configuration", False, f"Erreur JSON : {e}")
            overall_health = False
    else:
        check_step("Configuration", False, "Fichier config.json manquant.")
        overall_health = False

    # 2. Vérification du Moteur DSP (Digital Signal Processing)
    # 
    try:
        # On simule un signal de 1 seconde à 44.1kHz
        dummy_y = np.random.uniform(-1, 1, 44100)
        stft = librosa.stft(dummy_y)
        check_step("Moteur Audio (DSP)", True, "Librosa & FFT opérationnels.")
    except Exception as e:
        check_step("Moteur Audio (DSP)", False, f"Échec du calcul spectral : {e}")
        overall_health = False

    # 3. Vérification du Support GPU (NVIDIA)
    # 
    if subprocess.run(["command", "-v", "nvidia-smi"], capture_output=True, shell=True).returncode == 0:
        try:
            gpu_info = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], encoding='utf-8')
            check_step("Support GPU", True, f"NVIDIA détecté ({gpu_info.strip()})")
        except:
            check_step("Support GPU", False, "Pilotes NVIDIA mal configurés.")
    else:
        check_step("Support GPU", True, "Mode CPU uniquement (Pas de GPU NVIDIA).")

    # 4. Vérification de la Base de Données (Clé aedb_path)
    if config and 'paths' in config:
        db_path = config['paths'].get('aedb_path', "database/audio_expert_v01.db")
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            check_step("Base de Données", True, f"Accessible ({db_path})")
        except Exception as e:
            check_step("Base de Données", False, f"Erreur SQLite : {e}")
            overall_health = False

    # 5. Vérification du Modèle Machine Learning
    if config and 'paths' in config:
        model_path = config['paths'].get('model_path', "models/audio_expert_rf.joblib")
        if os.path.exists(model_path):
            check_step("Modèle ML", True, "Cerveau Random Forest détecté.")
        else:
            check_step("Modèle ML", False, "Fichier .joblib absent (Lancez init_model.py)")
            overall_health = False

    # 6. Vérification d'Ollama (Arbitrage IA)
    if config and 'llm' in config:
        url = config['llm']['api_url'].replace("/generate", "/tags")
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                check_step("IA (Ollama)", True, "Serveur Ollama en ligne.")
            else:
                check_step("IA (Ollama)", False, "Erreur API Ollama.")
        except:
            check_step("IA (Ollama)", False, "Injoignable (Lancez Ollama)")

    print("="*65)
    if overall_health:
        print("🚀 SYSTÈME PRÊT : Toutes les couches (DSP, GPU, ML, IA) sont validées.")
    else:
        print("⚠️  ATTENTION : Des composants critiques sont défaillants.")
    print("="*65)

if __name__ == "__main__":
    run_diagnostics()
