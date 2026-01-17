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
    print("="*50)
    print("🔍 AUDIO EXPERT PRO - DIAGNOSTIC SANTÉ V0.1")
    print("="*50)
    
    overall_health = True

    # 1. Vérification du fichier de Configuration
    config_ok = os.path.exists("config.json")
    if config_ok:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            check_step("Configuration", True, "config.json chargé avec succès.")
        except Exception as e:
            check_step("Configuration", False, f"Erreur de lecture : {e}")
            config_ok = False
    else:
        check_step("Configuration", False, "Fichier config.json manquant.")
    
    # 2. Vérification de l'Audio (Librosa & FFmpeg)
    try:
        # Création d'un signal dummy pour tester le moteur DSP
        dummy_y = np.random.uniform(-1, 1, 44100)
        stft = librosa.stft(dummy_y)
        check_step("Moteur Audio (DSP)", True, "Librosa & FFT opérationnels.")
    except Exception as e:
        check_step("Moteur Audio (DSP)", False, f"Erreur : {e}")
        overall_health = False

    # 3. Vérification GPU (NVIDIA-SMI)
    try:
        res = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], encoding='utf-8')
        check_step("GPU NVIDIA", True, f"Détecté : {res.strip()}")
    except:
        check_step("GPU NVIDIA", False, "Non détecté ou pilotes manquants (Mode CPU forcé).")

    # 4. Vérification Ollama (LLM API)
    if config_ok:
        url = config['llm']['api_url'].replace("/generate", "/tags") # Endpoint pour lister les modèles
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                target_model = config['llm']['model_name']
                if any(target_model in m for m in models):
                    check_step("LLM (Ollama)", True, f"Modèle '{target_model}' prêt.")
                else:
                    check_step("LLM (Ollama)", False, f"Ollama actif mais modèle '{target_model}' absent.")
            else:
                check_step("LLM (Ollama)", False, "Service Ollama injoignable.")
        except:
            check_step("LLM (Ollama)", False, "Service Ollama non lancé (port 11434).")

    # 5. Vérification de la Base de Données
    if config_ok:
        db_path = config['paths']['db_name']
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            check_step("Base de Données", True, f"SQLite accessible ({db_path}).")
        except Exception as e:
            check_step("Base de Données", False, f"Erreur : {e}")

    print("="*50)
    if overall_health:
        print("🚀 SYSTÈME OPÉRATIONNEL : Vous pouvez lancer app.py")
    else:
        print("⚠️  DÉFAUTS DÉTECTÉS : Veuillez corriger les points marqués '❌'")
    print("="*50)

if __name__ == "__main__":
    run_diagnostics()
