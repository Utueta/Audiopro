import json
from llm_service import LLMService

# Simulation de la configuration (normalement dans config.json)
mock_config = {
    "llm": {
        "model_name": "qwen2.5",
        "api_url": "http://localhost:11434/api/generate"
    }
}

def run_automated_test():
    llm = LLMService(mock_config)
    
    # --- SCÉNARIO 1 : Le Fake HQ (Doit être REJECT selon la hiérarchie) ---
    case_fake_hq = {
        "path": "/music/fake_hi_res.flac",
        "score": 0.45, # Score ML modéré
        "clipping": 0.01,
        "snr": 25.0,
        "is_fake_hq": 1.0, # CRITIQUE
        "phase_corr": 0.98,
        "meta": {"bitrate": 1411, "artist": "FakeArtist", "title": "Upscaled Track"}
    }

    # --- SCÉNARIO 2 : Qualité Studio (Doit être VALID) ---
    case_perfect = {
        "path": "/music/studio_master.wav",
        "score": 0.02,
        "clipping": 0.0,
        "snr": 35.0,
        "is_fake_hq": 0.0,
        "phase_corr": 0.99,
        "meta": {"bitrate": 2304, "artist": "ProAudio", "title": "Clean Track"}
    }

    test_cases = [
        ("TEST FAKE HQ", case_fake_hq),
        ("TEST STUDIO PERFECT", case_perfect)
    ]

    print(f"{'='*60}")
    print(f"🚀 DÉMARRAGE DES TESTS D'AUTOMATISATION V0.1")
    print(f"{'='*60}\n")

    for name, data in test_cases:
        print(f"🔍 Exécution : {name}")
        print(f"📊 Données envoyées : Score ML={data['score']}, FakeHQ={data['is_fake_hq']}")
        
        # Appel du service (Arbitrage Final)
        verdict = llm.get_verdict(data, history_context={"last_scan": "clean"})
        
        # Vérification du format de sortie strict
        if isinstance(verdict, dict) and "decision" in verdict:
            print(f"✅ FORMAT : JSON Valide détecté.")
            print(f"⚖️  DÉCISION : {verdict['decision']}")
            print(f"📝 RAISON : {verdict.get('reason', 'N/A')}")
            print(f"🎯 CONFIANCE : {verdict.get('confidence', 0)*100}%")
        else:
            print(f"❌ ERREUR : Le format de sortie n'est pas un JSON strict.")
            print(f"Réponse brute : {verdict}")
        
        print(f"{'-'*40}\n")

if __name__ == "__main__":
    # Note : Assure-toi qu'Ollama est lancé avant de tester
    try:
        run_automated_test()
    except Exception as e:
        print(f"💥 Crash du script de test : {e}")
