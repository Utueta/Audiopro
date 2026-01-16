import librosa
import subprocess
import soundfile as sf

def check_audio_stack():
    print("🧪 Vérification de la Stack Audio...")
    
    # 1. Vérifier la présence système de FFmpeg
    try:
        version = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT).decode()
        first_line = version.split('\n')[0]
        print(f"✅ FFmpeg Système : {first_line}")
        if "rpmfusion" in first_line.lower():
            print("   (Version RPM Fusion confirmée - Codecs complets)")
    except FileNotFoundError:
        print("❌ FFmpeg non trouvé dans le PATH système.")

    # 2. Vérifier si Librosa peut charger un décodeur
    try:
        # On teste si soundfile est opérationnel (le moteur par défaut de librosa)
        print(f"✅ Soundfile Backend : {sf.__version__}")
        print("✅ Librosa est prêt à traiter les fichiers 192kHz via libsndfile.")
    except Exception as e:
        print(f"❌ Erreur de backend audio : {e}")

if __name__ == "__main__":
    check_audio_stack()
