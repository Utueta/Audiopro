
import os, hashlib, numpy as np, librosa


class AudioAnalyzer:

    def __init__(self, config):

        self.cfg = config['audio']

        self.params = self.cfg['analysis_params']


    def get_metrics(self, file_path):

        # Hashage Blake2b (Identité unique)

        h = hashlib.blake2b(digest_size=16)

        with open(file_path, "rb") as f:

            while chunk := f.read(8192): h.update(chunk)

        

        # Moteur DSP (Physique du son)

        y, sr = librosa.load(file_path, sr=None, duration=self.cfg['sample_duration_sec'])

        s_mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)

        matrix = librosa.power_to_db(s_mel, ref=np.max)

        

        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

        clipping = np.sum(np.abs(y) >= (1.0 - self.params['clipping_sensitivity'])) / len(y)

        

        return {

            "filename": os.path.basename(file_path),

            "hash": h.hexdigest(),

            "matrix": matrix,

            "is_fake_hq": centroid < (self.params['fake_hq_threshold_khz'] * 1000),

            "clipping": float(clipping)

        }

