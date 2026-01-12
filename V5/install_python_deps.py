import subprocess
import sys

def install_packages():
    packages = [
        "PySide6",       # Interface graphique
        "librosa",       # Analyse audio
        "matplotlib",    # Graphiques et Waveforms
        "pandas",        # Gestion des données pour ML
        "scikit-learn",  # Machine Learning (Random Forest)
        "send2trash",    # Corbeille sécurisée
        "mutagen",       # Métadonnées (Tags)
        "requests",      # Connexion Ollama (LLM)
        "numpy",         # Calculs mathématiques
        "scipy"          # Traitement du signal
    ]

    print("--- Installation des bibliothèques Python ---")
    for package in packages:
        print(f"Installation de {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except Exception as e:
            print(f"Erreur lors de l'installation de {package}: {e}")

if __name__ == "__main__":
    install_packages()
