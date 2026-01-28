import os
import hashlib
import numpy as np
import librosa
import mutagen
import logging

class AudioAnalyzer:
    def __init__(self, config):
        self.cfg = config['audio']
        self.analysis_cfg = self.cfg['analysis_params']

    def get_metrics(self, file_path):
        """Pipeline d'analyse complet : Hash -> Metadata -> DSP."""
        try:
            # 1. Empreinte unique (Intégrité & Doublons)
            file_hash = self._generate_blake2b(file_path)
            
            # 2. Métadonnées & Bitrate
            metadata = self._get_metadata(file_path)
            
            # 3. Chargement Audio (échantillon de 45s comme défini en config)
            y, sr = librosa.load(file_path, sr=None, duration=self.cfg['sample_duration_sec'])
            
            # 4. Calcul de la matrice de rendu (STFT)
            # On calibre la fenêtre pour un rendu visuel fluide
            spectrogram_matrix = self._prepare_display_matrix(y)
            
            # 5. Calcul des indicateurs de fraude
            is_fake, cut_off = self._detect_fake_hq(y, sr)
            snr = self._calculate_snr(y)
            clipping = self._check_clipping(y)

            return {
                "hash": file_hash,
                "path": file_path,
                "matrix": spectrogram_matrix, # Matrice calibrée pour le Glow
                "is_fake_hq": is_fake,
                "cutoff_frequency": cut_off,
                "snr": snr,
                "clipping": clipping,
                "meta": metadata
            }
        except Exception as e:
            logging.error(f"Erreur d'analyse sur {file_path}: {e}")
            raise

    def _generate_blake2b(self, file_path):
        """Hashage ultra-rapide pour la base SQLite."""
        hash_obj = hashlib.blake2b(digest_size=16)
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def _prepare_display_matrix(self, y):
        """
        Calibre la matrice NumPy pour le rendu natif Qt.
        Applique une échelle de Mel et une conversion dB optimisée.
        """
        # Utilisation de melspectrogram pour une perception humaine (plus d'espace pour les hautes fréquences)
        S = librosa.feature.melspectrogram(y=y, sr=44100, n_mels=128, fmax=22050)
        S_db = librosa.power_to_db(S, ref=np.max)
        
        # On nettoie les valeurs extrêmes pour éviter les artefacts visuels
        # Le plancher est fixé à -80dB pour un noir pur dans l'interface Obsidian
        S_db = np.clip(S_db, -80, 0)
        return S_db

    def _detect_fake_hq(self, y, sr):
        """Détecte si le spectre s'arrête brutalement (Upscaling)."""
        # Calcul du centroïde spectral moyen
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        avg_centroid = np.mean(centroid)
        
        # Seuil basé sur la config (ex: 16.5 kHz)
        threshold = self.analysis_cfg['fake_hq_threshold_khz'] * 1000
        is_fake = avg_centroid < threshold
        return is_fake, avg_centroid

    def _calculate_snr(self, y):
        """Mesure le rapport Signal-sur-Bruit."""
        abs_y = np.abs(y)
        signal_power = np.mean(abs_y**2)
        noise_power = np.mean(librosa.effects.preemphasis(y)**2) / 100 # Estimation simplifiée
        return 10 * np.log10(signal_power / noise_power) if noise_power > 0 else 0

    def _check_clipping(self, y):
        """Détecte la saturation numérique (pics à 1.0 ou -1.0)."""
        max_val = np.max(np.abs(y))
        count_clipped = np.sum(np.abs(y) >= 0.99)
        return count_clipped / len(y)

    def _get_metadata(self, file_path):
        """Récupère les infos techniques via Mutagen."""
        audio = mutagen.File(file_path)
        return {
            "bitrate": getattr(audio.info, 'bitrate', 0) // 1000 if audio else 0,
            "samplerate": getattr(audio.info, 'sample_rate', 0) if audio else 0,
            "channels": getattr(audio.info, 'channels', 0) if audio else 0
        }
