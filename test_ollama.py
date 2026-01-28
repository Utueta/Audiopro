import requests
import json

def test_ollama_connection():
    url = "http://localhost:11434/api/generate"
    # Modifiez le nom du modèle si vous utilisez 'mistral' ou 'llama3'
    payload = {
        "model": "llama3", 
        "prompt": "Réponds 'OK' si tu reçois ce message.",
        "stream": False
    }

    print("🔍 Test de connexion à Ollama...")
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("✅ Connexion réussie !")
            print(f"🤖 Réponse du LLM : {response.json().get('response')}")
        else:
            print(f"⚠️ Erreur serveur (Code {response.status_code}).")
    except requests.exceptions.ConnectionError:
        print("❌ ÉCHEC : Ollama ne semble pas être lancé. (Tapez 'ollama serve' dans un terminal)")
    except Exception as e:
        print(f"❌ Erreur imprévue : {e}")

if __name__ == "__main__":
    test_ollama_connection()
