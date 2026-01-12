import numpy as np
import librosa

class SpectralExpert:
    def __init__(self):
        self.cutoff_threshold = 16500 # Seuil typique MP3 128-192kbps

    def detect_fake_hq(self, y, sr):
        """Analyse FFT pour détecter l'upscaling (Fake HQ)."""
        # Conversion en mono pour analyse spectrale
        if y.ndim > 1: y = librosa.to_mono(y)
        
        # Transformée de Fourier à court terme (STFT)
        stft = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)
        
        # Calcul du Spectral Roll-off (Fréquence où 95% de l'énergie disparaît)
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.95)[0]
        avg_rolloff = np.mean(rolloff)

        # Score de suspicion Fake HQ (0 à 1)
        # Si la coupure est < 16.5kHz sur un fichier censé être 44.1kHz+
        is_suspicious = 1.0 if avg_rolloff < self.cutoff_threshold else 0.0
        
        return {
            "spectral_cutoff": float(avg_rolloff),
            "fake_hq_probability": is_suspicious
        }
