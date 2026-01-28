import numpy as np
import librosa
import logging

class SpectralExpert:
    def __init__(self):
        """Expert Spectral - Version Consolidée (Segmentation & Centroid)."""
        self.n_fft = 2048
        self.logger = logging.getLogger("Audiopro.Spectral")

    def detect_fake_hq(self, y, sr):
        """
        [PRÉCISION] Analyse multi-segmentaire pour détecter les fraudes localisées.
        Plus-value : Détection des fichiers hybrides (Upscale partiel).
        """
        if y.size == 0:
            return {'fake_hq_probability': 0, 'spectral_cutoff': 0}

        # Conversion mono pour l'analyse spectrale si nécessaire
        y_mono = librosa.to_mono(y) if y.ndim > 1 else y
        
        # [RESTAURATION] Découpage en 3 segments stratégiques
        # Permet de vérifier la cohérence spectrale sur toute la durée
        segments = np.array_split(y_mono, 3)
        cutoffs = []

        for i, seg in enumerate(segments):
            # Calcul STFT par segment
            stft = np.abs(librosa.stft(seg, n_fft=self.n_fft))
            mean_spec = np.mean(stft, axis=1)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)
            
            # Seuil dynamique de détection de coupure (-60dB approx)
            threshold = np.max(mean_spec) * 0.001
            active_freqs = freqs[mean_spec > threshold]
            
            seg_cutoff = np.max(active_freqs) if active_freqs.size > 0 else 0
            cutoffs.append(seg_cutoff)
            self.logger.debug(f"Segment {i+1} cutoff: {seg_cutoff} Hz")

        # [SÉCURITÉ] On retient le cutoff le plus bas (le maillon faible du fichier)
        actual_cutoff = int(min(cutoffs))
        
        # Calcul de la probabilité de fraude basée sur les standards de codecs
        probability = 0.0
        if sr >= 44100:
            if actual_cutoff < 16000: probability = 0.98   # Profil MP3 128k
            elif actual_cutoff < 18500: probability = 0.75 # Profil MP3 320k
            elif actual_cutoff < 20000: probability = 0.25 # Compression légère
            else: probability = 0.02                       # Signal Full Range
            
        # [PLUS-VALUE] Calcul du Centroid Spectral (Luminosité du son)
        centroid = librosa.feature.spectral_centroid(y=y_mono, sr=sr)
        mean_centroid = float(np.mean(centroid))

        return {
            'fake_hq_probability': float(probability),
            'spectral_cutoff': actual_cutoff,
            'spectral_centroid': mean_centroid
        }
