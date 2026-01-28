"""
Audiopro Retraining Engine v0.3.1
- Role: Offline weight generation for AudioBrain.
- Logic: Pulls 'Ground Truth' from SQLite to evolve RF trees.
- Merged: Implements Atomic Transactions and Processed-Flagging.
"""

import joblib
import pandas as pd
import sqlite3
import logging
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Unified Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("system.retrain")

class BrainRetrainer:
    def __init__(self, db_path: str = "database/audiopro_v03.db", 
                 weights_dir: str = "core/brain/weights"):
        self.db_path = db_path
        self.weights_dir = Path(weights_dir)
        self.weights_dir.mkdir(parents=True, exist_ok=True)

    def execute_cycle(self) -> bool:
        """Runs the fit-persist-mark loop as a single atomic unit."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 1. Fetching human-corrected data not yet processed
            query = """
                SELECT file_hash, snr, clipping, final_verdict 
                FROM audits 
                WHERE final_verdict IS NOT NULL AND processed_for_training = 0
            """
            df = pd.read_sql(query, conn)

            if len(df) < 5:
                logger.info("Retrain: Insufficient data for training cycle (Need 5+ samples).")
                return False

            # 2. ML Feature Preparation
            X = df[['snr', 'clipping']]
            y = df['final_verdict'].apply(lambda x: 1 if x == 'CLEAN' else 0)

            # 3. Fit Z-Score Scaler (v0.2.5 requirement)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # 4. Train Random Forest
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_scaled, y)

            # 5. Persist artifacts for Hot-Reload
            joblib.dump(model, self.weights_dir / "random_forest_v0.3.pkl")
            joblib.dump(scaler, self.weights_dir / "scaler_v0.3.pkl")

            # 6. Mark as processed (Atomic Transaction)
            hashes = df['file_hash'].tolist()
            conn.executemany(
                "UPDATE audits SET processed_for_training = 1 WHERE file_hash = ?", 
                [(h,) for h in hashes]
            )
            conn.commit()
            
            logger.info(f"Retrain Success: {len(df)} samples processed. Artifacts updated.")
            return True
        except Exception as e:
            logger.error(f"Retrain Failure: {e}")
            return False
        finally:
            if conn: 
                conn.close()

if __name__ == "__main__":
    # Standardized execution point for v0.3.1
    retrainer = BrainRetrainer()
    retrainer.execute_cycle()
