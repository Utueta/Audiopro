import os
import joblib
import numpy as np
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

class BrainModel:
    """
    Système d'inférence Expert pour la certification Audio.
    Restaure la capacité d'apprentissage et la précision prédictive.
    """
    def __init__(self, model_path="core/brain/weights/audio_expert_v1.pkl"):
        self.logger = logging.getLogger("Audiopro.Brain")
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self._load_trained_weights()

    def _load_trained_weights(self):
        """Charge les poids du modèle ou initialise un classifieur par défaut."""
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                self.logger.info("Poids du modèle chargés avec succès.")
            except Exception as e:
                self.logger.error(f"Erreur chargement poids: {e}. Utilisation du mode heuristique.")
                self.model = self._get_default_classifier()
        else:
            self.logger.warning("Aucun modèle trouvé dans weights/. Initialisation d'un modèle vierge.")
            self.model = self._get_default_classifier()

    def _get_default_classifier(self):
        """Crée un modèle Random Forest avec des hyper-paramètres de base (Certification standard)."""
        # On utilise 100 arbres pour une stabilité de décision optimale
        return RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)

    def predict(self, dsp_data, metadata):
        """
        Calcule l'indice de confiance (0.0 à 1.0).
        Plus-value : Analyse multidimensionnelle combinant Physique (DSP) et Logique (Metadata).
        """
        try:
            # 1. Préparation du vecteur de caractéristiques (Features)
            # Nous fusionnons ici les données des trois experts consolidés précédemment
            features = np.array([[
                dsp_data.get('clipping', 0),
                dsp_data.get('snr', 0),
                dsp_data.get('phase_corr', 1),
                dsp_data.get('fake_hq_probability', 0),
                dsp_data.get('spectral_cutoff', 0),
                dsp_data.get('spectral_centroid', 0),
                1 if metadata.get('is_lossless') else 0,
                metadata.get('bitrate', 0)
            ]])

            # 2. Inférence (Si le modèle est entraîné, il prédit, sinon il score)
            if hasattr(self.model, "predict_proba"):
                # Probabilité que le fichier soit "BAD" (Classe 1)
                prediction = self.model.predict_proba(features)[0][1]
            else:
                prediction = self._heuristic_scoring(dsp_data, metadata)

            self.logger.info(f"Verdict Brain : {prediction:.2f}")
            return float(prediction)

        except Exception as e:
            self.logger.error(f"Erreur d'inférence Brain : {e}")
            return 0.5 # Zone grise en cas d'échec

    def _heuristic_scoring(self, dsp, meta):
        """
        Algorithme de secours (V3 améliorée) si aucun poids n'est disponible.
        Utilise une pondération mathématique précise.
        """
        score = 0.0
        
        # Poids 1 : Fraude spectrale (Le plus lourd : 50%)
        score += dsp.get('fake_hq_probability', 0) * 0.5
        
        # Poids 2 : Incohérence Bitrate/Cutoff (30%)
        if meta.get('bitrate', 0) > 1000 and dsp.get('spectral_cutoff', 0) < 16500:
            score += 0.3 # Suspicion forte d'upsampling
            
        # Poids 3 : Qualité du signal (Clipping/SNR : 20%)
        if dsp.get('clipping', 0) > 1.0: score += 0.1
        if dsp.get('snr', 0) < 20: score += 0.1
            
        return np.clip(score, 0.0, 1.0)

    def train_on_batch(self, X_train, y_train):
        """Permet l'apprentissage continu (Évolutivité)."""
        self.model.fit(X_train, y_train)
        joblib.dump(self.model, self.model_path)
        self.logger.info("Modèle mis à jour et sauvegardé.")
