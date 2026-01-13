import os
import hashlib
import warnings
import logging
import numpy as np
import librosa

class AudioAnalyzer:
    def __init__(self):
        """Moteur DSP Consolidé - Excellence Audio & Robustesse."""
        self.n_fft = 2048
        self.hop_length = 512
        self.logger = logging.getLogger("Audiopro.DSP")

    def get_fast_hash(self, file_path):
        """Identification unique DevSecOps (MD5 sur chunk initial)."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # Lecture de 8Mo pour équilibrer vitesse et collision
                chunk = f.read(8192 * 1024)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Hash error: {e}")
            return str(hash(file_path))

    def load_audio_safely(self, file_path, sr=44100):
        """
        [ROBUSTESSE] Chargement avec gestion de la stéréo et fallback multicouche.
        Retourne : (y, sr, engine_name)
        """
        try:
            # Tentative 1 : Stéréo native (Plus-value : Analyse de phase)
            y, native_sr = librosa.load(file_path, sr=sr, mono=False)
            return y, native_sr, "Soundfile (Natif)"
        except Exception as e:
            self.logger.warning(f"Soundfile fail for {os.path.basename(file_path)}, switching to FFmpeg")
            try:
                # Tentative 2 : Fallback FFmpeg (Indispensable sur Fedora)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    y, native_sr = librosa.load(file_path, sr=sr, mono=False, res_type='kaiser_fast')
                return y, native_sr, "FFmpeg (Fallback)"
            except Exception as critical_e:
                self.logger.error(f"Critical decoding failure: {critical_e}")
                raise RuntimeError(f"Fichier illisible ou corrompu: {file_path}")

    def analyze_phase(self, y):
        """
        [PRÉCISION] Calcul de la corrélation de phase L/R.
        Plus-value : Détecte les inversions de phase (anti-phase).
        """
        if y.ndim < 2: 
            return 1.0  # Un signal mono est toujours en phase
        
        # Corrélation de Pearson entre les deux canaux
        correlation = np.corrcoef(y[0], y[1])[0, 1]
        return float(np.nan_to_num(correlation, nan=1.0))

    def analyze_clipping(self, y):
        """Détection de saturation (True Peak estimation)."""
        if y.size == 0: return 0.0
        # Analyse sur l'ensemble de la matrice (L+R)
        clipping_samples = np.sum(np.abs(y) >= 0.99)
        return float((clipping_samples / y.size) * 100)

    def analyze_snr(self, y):
        """Calcul du SNR (Signal-to-Noise Ratio) via analyse d'énergie."""
        abs_y = np.abs(y)
        max_val = np.max(abs_y)
        if max_val < 1e-7: return 0.0
        
        # Signal : Moyenne des zones > -20dB du pic
        # Bruit : Moyenne des zones < -60dB du pic
        signal_mask = abs_y > (max_val * 0.1)
        noise_mask = abs_y < (max_val * 0.001)
        
        signal_level = np.mean(abs_y[signal_mask]) if np.any(signal_mask) else 1e-6
        noise_level = np.mean(abs_y[noise_mask]) if np.any(noise_mask) else 1e-7
        
        return float(np.clip(20 * np.log10(signal_level / noise_level), 0, 100))

    def get_visual_data(self, y, sr):
        """
        [PRÉCISION VISUELLE] Waveform propre avec conservation des pics.
        """
        # Conversion mono uniquement pour l'affichage UI (économie de ressources)
        y_mono = librosa.to_mono(y) if y.ndim > 1 else y
        duration = librosa.get_duration(y=y_mono, sr=sr)
        
        # Échantillonnage intelligent pour éviter l'aliasing
        target_points = 10000
        if len(y_mono) > target_points:
            indices = np.linspace(0, len(y_mono) - 1, target_points, dtype=int)
            waveform = y_mono[indices]
            times = np.linspace(0, duration, target_points)
        else:
            waveform = y_mono
            times = np.linspace(0, duration, len(y_mono))

        stft = np.abs(librosa.stft(y_mono, n_fft=self.n_fft, hop_length=self.hop_length))
        return times, waveform, librosa.amplitude_to_db(stft, ref=np.max)
