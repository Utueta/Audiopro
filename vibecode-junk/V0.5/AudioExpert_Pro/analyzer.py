import os, hashlib, numpy as np, librosa

class AudioAnalyzer:
    def __init__(self, config):
        self.cfg = config['audio']

    def get_metrics(self, path):
        if os.path.getsize(path) == 0: return {"status": "defective", "reason": "0kb"}
        
        y, sr = librosa.load(path, sr=None, duration=self.cfg['sample_duration_sec'])
        h = hashlib.blake2b(open(path, "rb").read(), digest_size=16).hexdigest()
        
        # Clipping & Crackling
        clipping = np.sum(np.abs(y) >= 0.95) / len(y)
        crackling = np.sum(np.abs(np.diff(y)) > 0.4) / len(y)
        
        # SNR
        rms = librosa.feature.rms(y=y)[0]
        snr = 20 * np.log10(np.mean(rms) / (np.std(y) + 1e-6))
        
        # Score Qualité (0-100)
        quality = 100 * (1.0 - min(clipping * 5 + crackling * 50, 0.9))
        
        # Matrix pour Spectrogramme
        s_mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        matrix = librosa.power_to_db(s_mel, ref=np.max)

        return {
            "filename": os.path.basename(path), "hash": h, "matrix": matrix,
            "clipping": float(clipping), "snr": float(snr), "crackling": float(crackling),
            "quality_score": float(quality), "centroid": float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))),
            "status": "ok"
        }

