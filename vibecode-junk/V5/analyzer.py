import librosa
import numpy as np
import hashlib
import os
from mutagen import File as MutagenFile

class AudioAnalyzer:
    def __init__(self, config):
        self.cfg = config['analysis_thresholds']
        self.w = config['ml_weights']

    def get_metrics(self, path):
        try:
            file_size = os.stat(path).st_size
            if file_size == 0: return self._create_empty_metric(path, "Taille 0kb")

            # Chargement en stéréo pour l'analyse de phase
            y, sr = librosa.load(path, sr=None, duration=45, mono=False)
            if y.size == 0: return self._create_empty_metric(path, "Durée 0")

            # Conversion mono pour certaines analyses signal
            y_mono = librosa.to_mono(y) if y.ndim > 1 else y
            
            # 1. Détection Fake HQ (Coupure spectrale)
            S = np.abs(librosa.stft(y_mono))
            freqs = librosa.fft_frequencies(sr=sr)
            power_per_freq = np.sum(S, axis=1)
            # On cherche si l'énergie au-dessus du seuil (ex: 16kHz) est négligeable
            idx_threshold = np.searchsorted(freqs, self.cfg['fake_hq_threshold_khz'] * 1000)
            high_freq_energy = np.sum(power_per_freq[idx_threshold:]) / np.sum(power_per_freq)
            is_fake_hq = 1.0 if high_freq_energy < 0.005 else 0.0

            # 2. Corrélation de Phase (Mono vs Stéréo)
            phase_corr = 1.0
            if y.ndim > 1:
                # Corrélation de Pearson entre canal L et R
                phase_corr = np.corrcoef(y[0], y[1])[0, 1]
            
            # 3. Métriques classiques (Clipping, SNR, Crackling)
            clipping = np.sum(np.abs(y_mono) >= self.cfg['clipping_threshold']) / len(y_mono)
            
            # SNR
            rms = librosa.feature.rms(y=y_mono)[0]
            snr = 20 * np.log10(max(np.max(rms), 1e-9) / max(np.percentile(rms, 10), 1e-9))
            
            # Score global avec Malus Fake HQ
            quality_base = 100 - (clipping * 100)
            suspicion = (self.w['w1_clipping'] * clipping) + \
                        (self.w['w2_snr'] * max(0, 15 - snr)) + \
                        (self.w['w4_quality'] * max(0, 60 - quality_base)) + \
                        (is_fake_hq * 30) # Malus important si Fake HQ
            
            return {
                "path": path, "clipping": float(clipping), "snr": float(snr),
                "score": float(max(0, min(1, suspicion / 100))),
                "is_fake_hq": is_fake_hq, "phase_correlation": float(phase_corr),
                "defect_timestamps": self._detect_defect_timestamps(y_mono, sr),
                "meta": self._get_tags(path, file_size), "status": "ok",
                "hash": self.get_hash(path), "duration": float(len(y_mono)/sr)
            }
        except Exception as e:
            return self._create_empty_metric(path, str(e))

    def _detect_defect_timestamps(self, y, sr):
        # (Logique identique à la version précédente)
        diff = np.abs(np.diff(y))
        indices = np.where(diff > (np.std(diff) * 5))[0]
        return sorted([float(i/sr) for i in indices[:10]])

    def _create_empty_metric(self, path, reason):
        return {"path": path, "score": 1.0, "status": "ban", "reason": reason, "hash": "0", "meta": {"bitrate":0, "size":0}}

    def _get_tags(self, path, size):
        tags = {"artist": "Inconnu", "title": "Inconnu", "bitrate": 0, "size": size}
        try:
            audio = MutagenFile(path)
            if audio and audio.info:
                tags["bitrate"] = getattr(audio.info, 'bitrate', 0) // 1000
        except: pass
        return tags

    @staticmethod
    def get_hash(path):
        h = hashlib.blake2b(digest_size=16)
        with open(path, "rb") as f:
            h.update(f.read(1024*512))
            if os.path.getsize(path) > 1024*1024:
                f.seek(-1024*512, 2)
                h.update(f.read(1024*512))
        return h.hexdigest()
