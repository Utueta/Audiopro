import numpy as np
import librosa

class AudioAnalyzer:
    def __init__(self, sample_rate=44100):
        self.target_sr = sample_rate

    def get_fast_hash(self, file_path):
        """Hash Blake2b partiel (64ko début / 64ko fin) pour performance atomique."""
        import hashlib
        h = hashlib.blake2b(digest_size=16)
        with open(file_path, "rb") as f:
            h.update(f.read(65536)) # Début
            try:
                f.seek(-65536, 2)
                h.update(f.read(65536)) # Fin
            except IOError:
                pass # Fichier trop petit
        return h.hexdigest()

    def load_audio_safely(self, file_path, duration=45):
        """Chargement optimisé : évite de charger 1Go en RAM."""
        # On ne charge que les 45 premières secondes pour l'analyse expert
        y, sr = librosa.load(file_path, sr=None, duration=duration, mono=False)
        return y, sr

    def analyze_clipping(self, y):
        """Détection du clipping (échantillons >= 0.98 FS)."""
        clipping_count = np.sum(np.abs(y) >= 0.98)
        return (clipping_count / y.size) * 100

    def analyze_phase(self, y):
        """Corrélation de phase entre L et R (Pearson).
        1.0 = Mono/Parfait, 0.0 = Stéréo large, -1.0 = Inversion de phase.
        """
        if y.ndim < 2: return 1.0 # Mono pur
        corr = np.corrcoef(y[0], y[1])[0, 1]
        return np.nan_to_num(corr, nan=1.0)

    def analyze_snr(self, y):
        """Estimation du SNR via le rapport signal/bruit de fond (RMS)."""
        rms_signal = np.sqrt(np.mean(y**2))
        # Estimation simple du bruit sur les zones les plus calmes
        noise_floor = np.percentile(np.abs(y), 10) 
        if noise_floor < 1e-9: return 90.0 # Silence quasi parfait
        snr = 20 * np.log10(rms_signal / (noise_floor + 1e-9))
        return np.clip(snr, 0, 100)
