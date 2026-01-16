import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import os

class BrainModel:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = self._load_or_init()
        self.buffer_size = 5 # Réentraînement tous les 5 feedbacks
        self.feedback_buffer = []

    def _load_or_init(self):
        """Charge le modèle existant ou initialise un Random Forest vierge."""
        if os.path.exists(self.model_path):
            try:
                return joblib.load(self.model_path)
            except:
                return self._create_new_model()
        return self._create_new_model()

    def _create_new_model(self):
        """Initialisation du modèle avec des poids équilibrés."""
        return RandomForestRegressor(n_estimators=100, random_state=42)

    def predict(self, features):
        """
        Calcule le score de suspicion [0.0 - 1.0].
        Features attendues: clipping, snr, phase, fake_hq
        """
        X = np.array([[
            features['clipping'], 
            features['snr'], 
            features['phase'], 
            features['fake_hq']
        ]])
        
        # Si le modèle n'est pas encore entraîné, retourne un score pondéré fixe
        try:
            return float(self.model.predict(X)[0])
        except:
            # Fallback : Formule de suspicion Cold Start
            score = (features['clipping'] * 0.4) + (features['fake_hq'] * 0.6)
            return np.clip(score, 0, 1)

    def add_feedback(self, features, label):
        """
        Enregistre une décision humaine pour le futur réentraînement.
        label: 1.0 pour BAN, 0.0 pour GOOD
        """
        X = [features['clipping'], features['snr'], features['phase'], features['fake_hq']]
        self.feedback_buffer.append((X, label))

        if len(self.feedback_buffer) >= self.buffer_size:
            self._retrain()

    def _retrain(self):
        """Réentraînement incrémental du modèle."""
        X_new = np.array([item[0] for item in self.feedback_buffer])
        y_new = np.array([item[1] for item in self.feedback_buffer])
        
        # Note: RandomForest ne supporte pas partial_fit, on réentraîne sur l'historique
        # Dans une version Senior, on chargerait ici les données de la DB pour fitter.
        self.model.fit(X_new, y_new)
        
        # Sauvegarde de l'évolution du "Cerveau"
        joblib.dump(self.model, self.model_path)
        self.feedback_buffer = [] # Vidage du buffer
