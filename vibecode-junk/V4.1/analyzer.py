import librosa
import numpy as np
import hashlib
import os
from difflib import SequenceMatcher
from mutagen import File as MutagenFile

class AudioAnalyzer:
    @staticmethod
    def get_metrics(path):
        y, sr = librosa.load(path, sr=None, duration=45)
        clipping = np.sum(np.abs(y) >= 0.98) / len(y)
        rms = librosa.feature.rms(y=y)
        snr = 20 * np.log10(np.mean(rms) / (np.std(rms) + 1e-6))
        rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.95))
        crackling = np.sum(np.abs(np.diff(y)) > 0.5) / len(y)
        
        # Calcul du point d'erreur (1er pic de clipping ou craquement)
        bad_idx = np.where((np.abs(y) >= 0.98) | (np.abs(np.insert(np.diff(y), 0, 0)) > 0.5))[0]
        error_ts = float(bad_idx[0]/sr if len(bad_idx) > 0 else 0)

        score = max(0, min(100, 100 - (clipping * 50 + crackling * 100 + (20/max(snr,1)))))
        
        return {
            "clipping": float(clipping), "snr": float(snr), "roll_off": float(rolloff),
            "crackling": float(crackling), "score": float(score), "timestamp": error_ts
        }

    @staticmethod
    def get_hash(path):
        h = hashlib.blake2b(digest_size=16)
        with open(path, "rb") as f:
            h.update(f.read(1024*1024))
        return h.hexdigest()

    @staticmethod
    def get_tags(path):
        try:
            audio = MutagenFile(path)
            if audio:
                artist = str(audio.get('TPE1', audio.get('artist', [''])[0]))
                title = str(audio.get('TIT2', audio.get('title', [''])[0]))
                return f"{artist.lower()}_{title.lower()}"
        except: pass
        return ""

    @staticmethod
    def fuzzy_ratio(a, b):
        return SequenceMatcher(None, a, b).ratio()
