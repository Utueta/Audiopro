import sqlite3
import pandas as pd
import joblib
import json
import os
import logging
from sklearn.ensemble import RandomForestRegressor

class AudioModel:
    def __init__(self, config_path="config.json"):
        # 1. Chargement de la configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 2. Synchronisation des chemins (Correction Critique)
        self.db_path = self.config['paths']['aedb_path']
        self.model_path = self.config['paths']['model_path']
        
        self.retrain_counter = 0
        self.retrain_interval = self.config['ml_engine'].get('retrain_every', 5)
        
        # 3. Initialisation de la base de données
        self._init_db()
        
        # 4. Chargement sécurisé du modèle
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            # Si absent, on crée un regressor par défaut
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            # Note: Il est préférable de lancer init_model.py avant.
