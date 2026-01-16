import joblib
import os
from sklearn.ensemble import RandomForestClassifier
import numpy as np

def create_initial_model(model_path):
    """Génère un modèle RF de base pour initialiser le système."""
    # Création du dossier si inexistant
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    # Données d'entraînement factices (4 features : spectral_cut, clipping, snr, phase)
    # X: [Fidélité, Propreté, Dynamique, Cohérence]
    X = np.array([
        [18000, 0.01, 30, 0.9], # Exemple de fichier Sain
        [12000, 0.08, 15, 0.4]  # Exemple de fichier Fraude
    ])
    y = np.array([0, 1]) # 0 = Original, 1 = Fake HQ

    model = RandomForestClassifier(n_estimators=10)
    model.fit(X, y)
    
    joblib.dump(model, model_path)
    print(f"✅ Modèle initial créé avec succès dans : {model_path}")

if __name__ == "__main__":
    import json
    with open("config.json") as f:
        cfg = json.load(f)
    create_initial_model(cfg['paths']['model_path'])
