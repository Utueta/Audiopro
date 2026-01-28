import numpy as np
import librosa

class SpectralExpert:
    def __init__(self):
        self.n_fft = 2048

    def detect_fake_hq(self, y, sr):
        """Analyse multi-segment pour détecter les 'Upscales' partiels."""
        y_mono = librosa.to_mono(y) if y.ndim > 1 else y
        
        # Découpage en 3 segments (début, milieu, fin) de 5 secondes
        segment_len = 5 * sr
        segments = []
        if len(y_mono) > segment_len * 3:
            segments = [y_mono[:segment_len], 
                        y_mono[len(y_mono)//2 : len(y_mono)//2 + segment_len], 
                        y_mono[-segment_len:]]
        else:
            segments = [y_mono]

        cutoffs = []
        for seg in segments:
            spec = np.abs(librosa.stft(seg, n_fft=self.n_fft))
            mean_spec = np.mean(spec, axis=1)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=self.n_fft)
            threshold = np.max(mean_spec) * 0.001
            active = freqs[mean_spec > threshold]
            cutoffs.append(np.max(active) if len(active) > 0 else 0)

        # On prend le cutoff le plus bas des 3 segments (le maillon faible)
        min_cutoff = min(cutoffs)
        
        prob = 0.0
        if sr >= 44100:
            if min_cutoff < 16000: prob = 0.95
            elif min_cutoff < 18500: prob = 0.60
            elif min_cutoff < 20000: prob = 0.20
            
        return {
            'fake_hq_probability': float(prob),
            'spectral_cutoff': int(min_cutoff),
            'spectral_centroid': float(np.mean(librosa.feature.spectral_centroid(y=y_mono, sr=sr)))
        }
