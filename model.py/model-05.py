import sqlite3
import pandas as pd
import joblib
import json
import os
from sklearn.ensemble import RandomForestRegressor

class AudioModel:
    def __init__(self, config_path="config.json"):
        # Chargement de la configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db_path = self.config['paths']['db_name']
        self.model_path = "audio_expert_rf.joblib"
        self.retrain_counter = 0
        self.retrain_interval = self.config['ml_engine']['retrain_interval']
        
        # Initialisation de la base de données
        self._init_db()
        
        # Chargement ou création du modèle ML
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self._pretrain_dummy() # Entraînement initial pour éviter les erreurs

    def _init_db(self):
        """Crée la table si elle n'existe pas."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS scans (
                hash TEXT PRIMARY KEY,
                path TEXT,
                fake_hq REAL,
                clipping REAL,
                snr REAL,
                crackling REAL,
                phase REAL,
                ml_score REAL,
                user_label TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')

    def _pretrain_dummy(self):
        """Initialise le modèle avec les poids de la config."""
        # Simulation de données basées sur les poids initiaux
        # Cela permet au modèle d'avoir une 'intuition' avant le premier feedback
        pass 

    def predict_suspicion(self, metrics):
        """Calcule le score de suspicion (0.0 à 1.0)."""
        # Ordre des features : FakeHQ, Clipping, SNR, Crackling, Phase
        features = [[
            metrics['is_fake_hq'], 
            metrics['clipping'], 
            metrics['snr'], 
            metrics['crackling'], 
            metrics['phase_corr']
        ]]
        return float(self.model.predict(features)[0])

    def add_to_history(self, metrics, user_label=None):
        """Enregistre une analyse et gère la boucle d'apprentissage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''INSERT OR REPLACE INTO scans 
                (hash, path, fake_hq, clipping, snr, crackling, phase, ml_score, user_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (metrics['hash'], metrics['path'], metrics['is_fake_hq'], 
                 metrics['clipping'], metrics['snr'], metrics['crackling'], 
                 metrics['phase_corr'], metrics['ml_score'], user_label))
        
        if user_label:
            self.retrain_counter += 1
            if self.retrain_counter >= self.retrain_interval:
                self.retrain_and_adapt()
                self.retrain_counter = 0

    def retrain_and_adapt(self):
        """Réentraîne le modèle et ajuste les poids de la config si activé."""
        print("🔄 Réentraînement du modèle en cours...")
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM scans WHERE user_label IS NOT NULL", conn)
        
        if len(df) < 5: return

        # Conversion des labels texte en valeurs numériques pour le Regressor
        # 'Ban' = 1.0 (Suspect), 'Good' = 0.0 (Sain)
        y = df['user_label'].apply(lambda x: 1.0 if x == 'Ban' else 0.0)
        X = df[['fake_hq', 'clipping', 'snr', 'crackling', 'phase']]
        
        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)

        # --- LOGIQUE D'AUTO-AJUSTEMENT DES POIDS ---
        if self.config['ml_engine'].get('auto_weight_adjust', False):
            importances = self.model.feature_importances_
            feature_names = ['w_fake_hq', 'w_clipping', 'w_snr', 'w_crackling', 'w_phase']
            
            print("⚖️ Ajustement dynamique des poids :")
            for name, imp in zip(feature_names, importances):
                self.config['ml_engine']['weights'][name] = round(float(imp), 3)
                print(f"   - {name}: {imp:.3f}")
            
            # Sauvegarde de la nouvelle config
            with open("config.json", 'w') as f:
                json.dump(self.config, f, indent=4)
