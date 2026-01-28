"""
Audiopro Integrity Tester v0.2.5
- Validates DSP -> ML -> LLM pipeline connectivity
- Generates a 440Hz test tone for calibration
- Verifies model weight loading
"""

import os
import numpy as np
import soundfile as sf
from pathlib import Path

# Core Component Imports
from core.analyzer.pipeline import analyze_file
from core.brain.random_forest import AudioBrain
from services.ollama_llm import OllamaLLM

def run_integrity_check():
    print("--- Audiopro System Validation ---")
    
    # 1. Create Test Artifact
    test_file = "test_tone.wav"
    sr = 44100
    t = np.linspace(0, 1, sr)
    # Generate a clean 440Hz sine wave
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(test_file, audio, sr)
    print(f"[1/4] Created synthetic test signal: {test_file}")

    # 2. Test DSP Pipeline
    print("[2/4] Executing DSP Pipeline...", end=" ")
    results = analyze_file(test_file)
    if results and results.snr_value > 0:
        print(f"PASSED (SNR: {results.snr_value:.2f}dB)")
    else:
        print("FAILED (Check librosa/soundfile installation)")

    # 3. Test ML Brain
    print("[3/4] Loading ML Brain...", end=" ")
    try:
        brain = AudioBrain(weights_dir="core/brain/weights")
        # Map AnalysisResult to feature vector
        features = [results.snr_value, results.clipping_count, results.suspicion_score]
        prediction = brain.predict(features)
        print(f"PASSED (Verdict: {prediction})")
    except Exception as e:
        print(f"FAILED (Error: {e}). Did you run init_model.py?")

    # 4. Test LLM Arbitration (Ollama)
    print("[4/4] Checking Ollama Service...", end=" ")
    llm = OllamaLLM()
    if llm.check_health():
        print("PASSED (Service Online)")
    else:
        print("SKIPPED (Ollama offline - this is normal if not installed)")

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print("\n--- Validation Complete ---")

if __name__ == "__main__":
    run_integrity_check()
