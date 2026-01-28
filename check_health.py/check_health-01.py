import sys
import psutil
import requests

def check_system():
    health = {"gpu": False, "ollama": False}
    
    # Check Ollama status
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            health["ollama"] = True
    except:
        pass

    # Check GPU availability via pynvml or similar
    # (Simplified for health check hook)
    return all(health.values())

if __name__ == "__main__":
    sys.exit(0 if check_system() else 1)
