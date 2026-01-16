import sys
import importlib
import subprocess
import psutil
import platform

def check_package(package_name, min_version=None):
    try:
        lib = importlib.import_module(package_name)
        version = getattr(lib, "__version__", "Inconnue")
        print(f"✅ {package_name} installé (Version: {version})")
        return True
    except ImportError:
        print(f"❌ {package_name} MANQUANT")
        return False

def check_system_resources():
    print("\n--- Diagnostic Système ---")
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    print(f"RAM Totale : {total_gb:.2f} GB")
    if total_gb < 8:
        print("⚠️ Attention : Moins de 8GB de RAM. Risque de ralentissement sur fichiers 192kHz.")
    
    print(f"Système : {platform.system()} {platform.release()}")
    print(f"Python : {sys.version.split()[0]}")

def check_ollama():
    print("\n--- Diagnostic IA (Ollama) ---")
    try:
        # Tente de lister les modèles pour voir si le serveur répond
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            if "qwen2.5" in result.stdout.lower():
                print("✅ Ollama est actif et le modèle Qwen 2.5 est présent.")
            else:
                print("⚠️ Ollama est actif mais Qwen 2.5 n'a pas été trouvé. Lancez 'ollama pull qwen2.5'.")
        else:
            print("❌ Ollama est installé mais le service ne répond pas.")
    except FileNotFoundError:
        print("❌ Ollama n'est pas installé ou absent du PATH.")

def main():
    print("🔍 VÉRIFICATION DE L'ENVIRONNEMENT AUDIO EXPERT PRO V2.0\n")
    
    check_system_resources()
    
    print("\n--- Dépendances Python ---")
    dependencies = [
        "PySide6",    # Interface Graphique
        "librosa",    # Analyse DSP
        "numpy",      # Calculs matriciels
        "sklearn",    # Machine Learning (Random Forest)
        "matplotlib", # Spectrogrammes
        "mutagen",    # Métadonnées Codecs
        "psutil",     # Monitoring RAM/CPU
        "joblib"      # Persistance du modèle ML
    ]
    
    missing = 0
    for dep in dependencies:
        if not check_package(dep):
            missing += 1
            
    check_ollama()
    
    if missing > 0:
        print(f"\n❌ Il manque {missing} dépendance(s).")
        print("👉 Installez-les avec : pip install -r requirements.txt")
    else:
        print("\n🚀 Tout est prêt pour le lancement !")

if __name__ == "__main__":
    main()
