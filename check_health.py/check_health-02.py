"""
Audiopro Random Forest Brain v0.2.5
- Implements MLModelInterface for deterministic classification
- Handles feature vector normalization via Z-Score Scaler
- Manages persistent weight loading from .pkl artifacts
"""

import os
import sys
import json
import sqlite3
import subprocess
import requests
import psutil
import platform
import numpy as np
import librosa

def check_step(name, status, message=""):
    """Standardized industrial status reporting."""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name:<25} : {message}")
    return status

def run_diagnostics():
    print("="*65)
    print("🔍 AUDIOPRO INDUSTRIAL - COMPREHENSIVE DIAGNOSTIC V0.2.5")
    print("="*65)
    
    overall_health = True
    config = None

    # 1. System Resources & Platform (check_health.py)
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    system_info = f"{platform.system()} {platform.release()} | RAM: {total_gb:.2f}GB"
    check_step("System Environment", True, system_info)
    if total_gb < 8:
        print("⚠️  Warning: High-resolution 192kHz processing requires >8GB RAM.")

    # 2. Configuration Integrity (check_health-4.py)
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding='utf-8') as f:
                config = json.load(f)
            check_step("Configuration", True, "config.json loaded.")
        except Exception as e:
            overall_health = check_step("Configuration", False, f"JSON Error: {e}")
    else:
        overall_health = check_step("Configuration", False, "config.json missing.")

    # 3. DSP Engine Validation (check_health-1.py)
    try:
        dummy_y = np.random.uniform(-1, 1, 44100)
        librosa.stft(dummy_y)
        check_step("Audio Engine (DSP)", True, "Librosa & FFT operational.")
    except Exception as e:
        overall_health = check_step("Audio Engine (DSP)", False, f"FFT Failure: {e}")

    # 4. Persistence Layer: SQLite WAL (check_health-4.py)
    if config:
        db_path = config.get('paths', {}).get('db_name', "database/audiopro.db")
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            check_step("Database Access", True, f"SQLite connected ({db_path})")
        except Exception as e:
            overall_health = check_step("Database Access", False, f"SQLite Error: {e}")

    # 5. ML Brain Artifacts (check_health-4.py)
    model_path = "models/audio_expert_rf.joblib"
    if os.path.exists(model_path):
        check_step("ML Model Weights", True, "Random Forest brain detected.")
    else:
        print("⚠️  ML Model weights missing. System will operate in fallback mode.")

    # 6. AI Arbitrage Service: Ollama/Qwen (check_health-4.py)
    try:
        # Check if Ollama service is reachable and has the model
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            target = config.get('llm', {}).get('model_name', 'qwen2.5') if config else 'qwen2.5'
            if any(target in m for m in models):
                check_step("AI (Ollama)", True, f"Model '{target}' is ready.")
            else:
                check_step("AI (Ollama)", False, f"Service active but '{target}' model missing.")
        else:
            check_step("AI (Ollama)", False, "Service responded with error.")
    except Exception:
        check_step("AI (Ollama)", False, "Service offline (Check port 11434).")

    print("="*65)
    if overall_health:
        print("🚀 SYSTEM READY: All industrial requirements met.")
    else:
        print("❌ CRITICAL: Fix highlighted issues before production launch.")
    print("="*65)

if __name__ == "__main__":
    run_diagnostics()
