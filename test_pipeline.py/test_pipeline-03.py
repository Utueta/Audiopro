import os
import json
import time
from analyzer import AudioAnalyzer
from model import AudioModel
from llm_service import LLMService

# 1. Préparation de la configuration de test
config = {
    "paths": {"db_name": "test_automation.db"},
    "analysis_thresholds": {
        "clipping_threshold": 0.99,
        "snr_bad_threshold_db": 15.0,
        "fake_hq_threshold_khz": 16.0
    },
    "ml_weights": {
        "w1_clipping": 30.0, "w2_snr": 15.0, "w3_crackling": 15.0, "w4_fake_hq": 40.0
    },
    "llm": {
        "model_name": "qwen2.5",
        "api_url": "http://localhost:11434/api/generate"
    }
}

def run_pipeline_test(file_path):
    print(f"🚀 DÉMARRAGE DU PIPELINE AUTOMATISÉ (V0.1)")
    print(f"📄 Fichier cible : {file_path}\n")

    # Initialisation des composants
    analyzer = AudioAnalyzer(config)
    model = AudioModel(config['paths']['db_name'])
    llm = LLMService(config)

    # ÉTAPE 1 : Analyse Physique
    print("🧪 Étape 1 : Analyse du signal...")
    metrics = analyzer.get_metrics(file_path)
    print(f"✅ Métriques extraites : SNR={metrics['snr']:.2f}, FakeHQ={metrics['is_fake_hq']}")

    # ÉTAPE 2 : Prédiction ML & Stockage
    print("🤖 Étape 2 : Prédiction Machine Learning...")
    metrics['ml_score'] = model.predict_suspicion(metrics)
    model.add_to_queue(metrics)
    print(f"✅ Score ML calculé : {metrics['ml_score']:.4f}")

    # ÉTAPE 3 : Arbitrage LLM (Sortie JSON Stricte)
    print("⚖️  Étape 3 : Arbitrage final par IA...")
    # On passe un contexte historique vide pour ce test
    final_verdict = llm.get_verdict(metrics, history_context={"status": "new_file"})

    # ÉTAPE 4 : Validation de l'Automatisation
    print(f"\n{'='*40}")
    print("📊 RAPPORT FINAL D'AUTOMATISATION")
    print(f"{'='*40}")
    
    if "decision" in final_verdict:
        print(f"DÉCISION  : {final_verdict['decision']}")
        print(f"RAISON    : {final_verdict['reason']}")
        print(f"CONFIANCE : {final_verdict.get('confidence', 0)*100}%")
        
        # Exemple d'action automatisée
        if final_verdict['decision'] == "REJECT":
            print("🚫 ACTION : Fichier marqué pour suppression/quarantaine.")
        else:
            print("🎉 ACTION : Fichier validé pour la bibliothèque.")
    else:
        print("❌ ERREUR : Le format de sortie LLM n'est pas conforme au JSON strict.")

if __name__ == "__main__":
    # Remplace par un chemin vers un fichier audio existant pour tester
    TEST_FILE = "ton_fichier_test.mp3" 
    
    if os.path.exists(TEST_FILE):
        run_pipeline_test(TEST_FILE)
    else:
        print(f"⚠️  Veuillez placer un fichier '{TEST_FILE}' dans le dossier pour lancer le test.")
