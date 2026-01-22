"""
Audiopro Industrial Test Suite v0.3.1
- DSP Determinism Verification
- Blake2b Consistency Checks for 5-year traceability
"""

import pytest
import numpy as np
from core.analyzer.pipeline import calculate_snr, generate_hash

def test_blake2b_consistency(tmp_path):
    """VERIFY: Blake2b hashing remains constant for database traceability."""
    test_file = tmp_path / "test.pcm"
    content = b"INDUSTRIAL_AUDIO_DATA_V031"
    test_file.write_bytes(content)
    
    hash_1 = generate_hash(str(test_file))
    hash_2 = generate_hash(str(test_file))
    
    assert hash_1 == hash_2
    assert len(hash_1) == 128  # Blake2b 512-bit hex length
