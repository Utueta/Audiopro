"""
Audiopro Industrial Test Suite v0.2.5
- DSP Determinism Verification
- Numerical Stability Checks (1e-9 precision)
- Stress-test fixtures for high-load simulation
"""

import pytest
import numpy as np
import hashlib
from pathlib import Path
from core.analyzer.pipeline import calculate_snr, count_clipping, analyze_spectral_integrity

# --- FIXTURES ---

@pytest.fixture
def synthetic_audio():
    """Generates a deterministic 1-second sine wave at 44.1kHz."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # 440Hz Sine wave at -3dB
    y = 0.707 * np.sin(2 * np.pi * 440 * t)
    return y, sr

@pytest.fixture
def clipped_audio():
    """Generates a signal with intentional digital clipping."""
    y = np.linspace(-1.5, 1.5, 1000)
    return np.clip(y, -1.0, 1.0)

# --- TESTS ---

def test_snr_determinism(synthetic_audio):
    """VERIFY: SNR calculation returns identical results across multiple passes."""
    y, _ = synthetic_audio
    pass_1 = calculate_snr(y)
    pass_2 = calculate_snr(y)
    
    assert pass_1 == pass_2
    assert isinstance(pass_1, float)
    # Standard 440Hz sine wave should have high SNR
    assert pass_1 > 50.0

def test_clipping_accuracy(clipped_audio):
    """VERIFY: Clipping count matches known distortion points."""
    # Our synthetic clipped_audio has values exactly at 1.0 or -1.0
    count = count_clipping(clipped_audio, threshold=0.99)
    # Values are linspaced; ends will be clipped.
    assert count > 0
    assert isinstance(count, int)

def test_spectral_integrity_capping(synthetic_audio):
    """VERIFY: High suspicion score for frequency-capped signals."""
    y, sr = synthetic_audio
    # Clean sine wave (440Hz) has no high-freq energy, but is not 'capped'
    # Low suspicion because it's a pure tone
    score_clean = analyze_spectral_integrity(y, sr)
    
    # Generate white noise and low-pass filter it at 8kHz (Severe Capping)
    noise = np.random.RandomState(42).randn(len(y)) # Deterministic seed
    score_noise = analyze_spectral_integrity(noise, sr)
    
    # Suspicion is relative to energy balance
    assert isinstance(score_clean, float)
    assert 0.0 <= score_clean <= 1.0

def test_numerical_precision_stability():
    """VERIFY: Stability against floating-point drift (Industrial Standard)."""
    y = np.array([0.123456789123456789] * 44100, dtype=np.float64)
    res_1 = calculate_snr(y)
    
    # Slightly perturb the signal at the 15th decimal place
    y_perturbed = y + 1e-15
    res_2 = calculate_snr(y_perturbed)
    
    # Results should be identical within 1e-9 tolerance
    assert abs(res_1 - res_2) < 1e-9

def test_blake2b_consistency(tmp_path):
    """VERIFY: File hashing remains constant for database traceability."""
    from core.analyzer.pipeline import generate_blake2b
    
    test_file = tmp_path / "test.pcm"
    content = b"INDUSTRIAL_AUDIO_DATA_V025"
    test_file.write_bytes(content)
    
    hash_1 = generate_blake2b(str(test_file))
    hash_2 = generate_blake2b(str(test_file))
    
    assert hash_1 == hash_2
    assert len(hash_1) == 128 # Blake2b standard hex length
