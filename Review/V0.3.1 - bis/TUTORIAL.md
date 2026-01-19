"""
Audiopro v0.3.1
Handles the documentation triage and user operational manual.
"""

# Audiopro Expert Tutorial v0.3.1

This manual provides the operational framework for using the **Audiopro Sentinel System**.

---

## 1. System Preparation
* [cite_start]**Ollama Service**: Ensure Ollama is running with `qwen2.5` for arbitration.
* [cite_start]**Database Integrity**: The system uses `audiopro_v03.db` in WAL mode for concurrent I/O[cite: 7].
* [cite_start]**Traceability**: Files are hashed using **Blake2b** for 5-year maintenance tracking.

---

## 2. Result Arbitration
The Sentinel logic uses a multi-tier verification:
1. [cite_start]**Local ML**: Random Forest classifies files[cite: 4].
2. **LLM Fallback**: Triggered for suspicion scores between **0.35 and 0.75**.
3. **Verdict**: Final status (CLEAN/CORRUPT) is stored with a technical justification.

---

## 3. Maintenance
* [cite_start]**Logs**: Check `logs/analysis.log` for DSP math traces[cite: 6].
* [cite_start]**Health**: Run `scripts/check_health.py` to verify GPU and LLM availability[cite: 11].
