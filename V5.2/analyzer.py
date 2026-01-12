import os
import hashlib
import numpy as np
import librosa
import soundfile as sf
from mutagen import File as MutagenFile

class AudioAnalyzer:
    def __init__(self, config):
        self.config = config
        self.sample_duration = self.config['audio']['sample_duration_sec']
        self.cutoff_khz = self.config['analysis_thresholds']['fake_hq_cutoff_khz']

    def get_metrics(self, file_path):
        """
        Analyse complète du fichier. 
        Garantit : Hash Blake2b, Métadonnées Mutagen et 5 métriques physiques.
        """
        try:
            # 1. Empreinte Numérique (Hash Blake2b 128-bit)
            file_hash = self._generate_blake2b(file_path)

            # 2. Extraction Métadonnées (Mutagen)
            metadata = self._get_metadata(file_path)

            # 3. Chargement Audio (Échantillonnage performant)
            y, sr = librosa.load(file_path, sr=None, duration=self.sample_duration)
            
            # 4. Calcul des métriques physiques
            metrics = {
                "hash": file_hash,
                "path": file_path,
                "meta": metadata,
                "clipping": self._check_clipping(y),
                "snr": self._calculate_snr(y),
                "crackling": self._detect_crackling(y),
                "phase_corr": self._check_phase(file_path), # Nécessite chargement stéréo
                "is_fake_hq": self._detect_fake_hq(y, sr)
            }
            return metrics
        except Exception as e:
            print(f"❌ Erreur analyse {file_path}: {e}")
            return None

    def _generate_blake2b(self, file_path):
        """Génère un hash unique basé sur le contenu binaire."""
        hash_obj = hashlib.blake2b(digest_size=16)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def _get_metadata(self, file_path):
        """Récupère Bitrate, Artiste et Titre."""
        audio = MutagenFile(file_path)
        return {
            "bitrate": int(audio.info.bitrate / 1000) if hasattr(audio.info, 'bitrate') else 0,
            "artist": audio.get('artist', ['Inconnu'])[0],
            "title": audio.get('title', ['Inconnu'])[0],
            "samplerate": audio.info.sample_rate if hasattr(audio.info, 'sample_rate') else 0
        }

    def _check_clipping(self, y):
        """Détecte la saturation (pics proches de 1.0)."""
        max_val = np.max(np.abs(y))
        return 1.0 if max_val >= self.config['analysis_thresholds']['clipping_threshold'] else float(max_val)

    def _calculate_snr(self, y):
        """Mesure le Signal-to-Noise Ratio approximatif."""
        abs_y = np.abs(y)
        signal = np.mean(abs_y[abs_y > np.max(abs_y) * 0.1]) # Signal utile
        noise = np.mean(abs_y[abs_y < np.max(abs_y) * 0.01])  # Bruit de fond
        if noise == 0: return 50.0
        snr = 20 * np.log10(signal / noise)
        return float(np.clip(snr, 0, 50))

    def _detect_fake_hq(self, y, sr):
        """
        Détection d'Upscaling (Fake HQ).
        Analyse l'énergie spectrale au-dessus du seuil (16kHz).
        """
        # Transformation de Fourier
        stft = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)
        
        # Calcul de l'énergie au-delà du cutoff khz
        idx_cutoff = np.where(freqs >= (self.cutoff_khz * 1000))[0][0]
        energy_above = np.sum(stft[idx_cutoff:, :])
        energy_total = np.sum(stft)
        
        ratio = energy_above / energy_total
        # Si ratio infime, c'est un Fake HQ (Coupure nette)
        return 1.0 if ratio < 0.001 else 0.0

    def _detect_crackling(self, y):
        """Identification des craquements (dérivée brusque de l'amplitude)."""
        diff = np.diff(y)
        crackles = np.sum(np.abs(diff) > self.config['analysis_thresholds']['crackling_sensitivity'])
        return float(np.clip(crackles / len(y) * 100, 0, 1.0))

    def _check_phase(self, file_path):
        """Vérifie la corrélation stéréo (1.0 = Mono/Parfait, -1.0 = Hors phase)."""
        try:
            y_stereo, sr = librosa.load(file_path, sr=None, mono=False, duration=10)
            if y_stereo.ndim < 2: return 1.0 # Déjà mono
            corr = np.corrcoef(y_stereo[0], y_stereo[1])[0, 1]
            return float(corr)
        except:
            return 1.0
