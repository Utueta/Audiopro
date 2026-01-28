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
            if file_size == 0: return self._create_empty_metric(path, "Fichier vide")

            # Chargement (Stéréo pour phase, 45s max)
            y, sr = librosa.load(path, sr=None, duration=45, mono=False)
            y_mono = librosa.to_mono(y) if y.ndim > 1 else y

            # 1. Détection Fake HQ (Coupure spectrale)
            stft = np.abs(librosa.stft(y_mono))
            freqs = librosa.fft_frequencies(sr=sr)
            avg_power = np.mean(stft, axis=1)
            idx_16khz = np.searchsorted(freqs, self.cfg['fake_hq_threshold_khz'] * 1000)
            high_freq_ratio = np.sum(avg_power[idx_16khz:]) / (np.sum(avg_power) + 1e-9)
            is_fake_hq = 1.0 if high_freq_ratio < 0.002 else 0.0

            # 2. Corrélation de Phase
            phase_corr = 1.0
            if y.ndim > 1:
                phase_corr = float(np.corrcoef(y[0], y[1])[0, 1])

            # 3. Métriques Signal
            clipping = np.sum(np.abs(y_mono) >= self.cfg['clipping_threshold']) / len(y_mono)
            rms = librosa.feature.rms(y=y_mono)[0]
            snr = 20 * np.log10(max(np.max(rms), 1e-9) / max(np.percentile(rms, 10), 1e-9))

            # Score de suspicion initial
            suspicion = (self.w['w1_clipping'] * clipping) + \
                        (self.w['w2_snr'] * max(0, 18 - snr)) + \
                        (is_fake_hq * 35.0)

            return {
                "path": path, "hash": self.get_hash(path), "status": "ok",
                "score": float(max(0, min(1, suspicion / 100))),
                "clipping": float(clipping), "snr": float(snr),
                "is_fake_hq": is_fake_hq, "phase_corr": phase_corr,
                "defect_timestamps": self._detect_defects(y_mono, sr),
                "meta": self._get_tags(path, file_size)
            }
        except Exception as e:
            return self._create_empty_metric(path, str(e))

    def _detect_defects(self, y, sr):
        diff = np.abs(np.diff(y))
        indices = np.where(diff > (np.std(diff) * 5))[0]
        return sorted(list(set([round(float(i/sr), 2) for i in indices[:10]])))

    def _get_tags(self, path, size):
        tags = {"artist": "Inconnu", "title": os.path.basename(path), "bitrate": 0, "size": size}
        try:
            m = MutagenFile(path)
            if m:
                tags["artist"] = str(m.get('artist', ['Inconnu'])[0])
                tags["title"] = str(m.get('title', [os.path.basename(path)])[0])
                if m.info: tags["bitrate"] = getattr(m.info, 'bitrate', 0) // 1000
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

    def _create_empty_metric(self, path, reason):
        return {"path": path, "score": 1.0, "status": "ban", "reason": reason, "hash": "0", 
                "meta": {"artist":"N/A","title":"N/A","bitrate":0, "size":0}}
