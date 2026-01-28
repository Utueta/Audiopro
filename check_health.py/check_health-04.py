
import sys, os, requests


def check():

    print("📋 Diagnostic Audio Expert Pro V0.2.4")

    # Check Ollama

    try:

        requests.get("http://localhost:11434/api/tags", timeout=1)

        print("✅ Ollama : CONNECTÉ")

    except:

        print("❌ Ollama : HORS-LIGNE")

    

    # Check Venv

    if sys.base_prefix != sys.prefix:

        print("✅ Environnement Virtuel : OK")

    else:

        print("⚠️ Attention : Non exécuté dans un Venv")


if __name__ == "__main__": check()

--- 
