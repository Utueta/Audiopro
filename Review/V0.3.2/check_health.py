"""
Audiopro Health Diagnostics v0.3.1 (Hardened Merge)
- Role: Verifies OS binaries, Python libs, and Hardware status.
- Logic: Checks for libmagic, FFmpeg, CUDA (pynvml), and Ollama API.
"""

import subprocess
import magic
import requests
import pynvml
import logging

def check_status():
    print("--- Audiopro Industrial Suite: Hardened Pre-Flight Check ---\n")
    
    # 1. Security Gate (libmagic) - Critical for Pipeline.py
    try:
        m = magic.Magic(mime=True)
        print("[✓] Security: libmagic is functional.")
    except Exception:
        print("[!] Security: libmagic1 (OS Binary) missing.")

    # 2. DSP Gate (ffmpeg)
    try:
        ffmpeg_check = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        print("[✓] DSP: FFmpeg binary detected.") if ffmpeg_check.returncode == 0 else print("[!] DSP: FFmpeg error.")
    except FileNotFoundError:
        print("[!] DSP: FFmpeg not found in system PATH.")

    # 3. LLM Bridge (Ollama Connectivity)
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=2)
        print("[✓] Intelligence: Ollama API Online.") if res.status_code == 200 else print("[!] Intelligence: Ollama Service offline.")
    except Exception:
        print("[!] Intelligence: Ollama unreachable (Bridge disabled).")

    # 4. Hardware Check (pynvml Merge)
    try:
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        print(f"[✓] Hardware: {device_count} NVIDIA GPU(s) detected via NVML.")
        pynvml.nvmlShutdown()
    except Exception:
        print("[i] Hardware: CUDA/NVML not available. System will use CPU.")

    print("\n--- Diagnostics Complete ---")

if __name__ == "__main__":
    check_status()
