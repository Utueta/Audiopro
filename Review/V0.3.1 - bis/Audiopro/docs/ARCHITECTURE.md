#"""
# Audiopro v0.3.1
# - Industrial-grade system architecture documentation.
# - Implements Hexagonal (Ports-and-Adapters) design.
# - Enforces deterministic DSP, persistent ML, and conditional LLM arbitration.
#"""

# Architecture Overview

Audiopro implements a **hexagonal (ports-and-adapters)** design to ensure forensic integrity, scalability, and ≥5-year maintainability. The system maintains a strict separation between:

- **Core (Domain + Application Services):** Deterministic DSP feature extraction, ML Sentinel (Random Forest), and arbitration policies.
- **Infrastructure (Adapters):** SQLite repository (WAL mode), model weight persistence (`.pkl`), filesystem I/O, and health check scripts.
- **UI (Adapter):** PySide6 dashboard, real-time Matplotlib graphs/gauges, and human feedback capture.
- **External Services (Adapter):** Ollama/Qwen 2.5 arbitration backend with automated fallback logic.

---

## 1. Authoritative Runtime Entry
There is a single authoritative entrypoint (`app.py`) which coordinates the system lifecycle:
1. **Configuration:** Loads global parameters from `config.json` (weights, thresholds, paths).
2. **Diagnostics:** Triggers `splash_screen.py` to run pre-flight health checks via `scripts/check_health.py` and `scripts/smi.sh`.
3. **Hardware Fallback:** If `check_health.py`, `smi.sh`, or `splash_screen.py` fail to detect a valid GPU environment, the system automatically defaults to **CPU-based LLM inference**.
4. **GPU Detection:** `splash_screen.py` now detects CUDA/GPU absence and triggers CPU/RAM fallback.
5. **Dependency Injection:** Wires infrastructure adapters to core ports.
6. **Execution:** Starts the Qt event loop and initializes the `manager.py` orchestrator.

---

## 2. Data Contracts (Traceability)
All pipeline stages communicate via immutable data objects to prevent side effects:
- **`AudioArtifactIdentity`:** Content hash (Blake2b 128-bit), file size, and metadata.
- **`AudioFeatures`:** Deterministic DSP features (SNR, Clipping, Spectral Roll-Off, Phase Correlation, Crackling Density).
- **`AnalysisDecision`:** Suspicion score [0.0 - 1.0], verdict, and arbitration provenance.
- **`AuditFeedback`:** Human-corrected labels ([Good]/[Defective]) for incremental ML training.

---

## 3. Threading / Concurrency Model
To maintain an "Expert Audit Interface" responsiveness, the threading model is strictly segregated:
- **Main Thread:** Reserved for PySide6 UI rendering and user interaction. No blocking I/O or DSP permitted.
- **Worker Pool:** `QThreadPool` executes all `QRunnable` tasks for DSP, ML inference, and SQLite writes.
- **QThreadPool Monitoring:** Real-time tracking of active vs. available threads to prevent pipeline starvation.
- **Utilization Monitoring:** Real-time tracking of active vs. available threads in the pool to prevent pipeline starvation.
- **Async Integration:** Asynchronous services (Ollama) run via a managed bridge to prevent event loop blocking.
- **Cancellation:** All workers support cancellation signals for safe resource release during shutdown.

---

## 4. Deterministic DSP Subsystem
Feature extraction is deterministic: identical input bytes and configuration will yield identical features.
- **Segmented Loading:** Only the first 45s of audio are analyzed to optimize RAM (approx. 7.5MB per file).
- **Stratified Sampling:** Option for segmented loading (30s intro, 10s middle, 10s outro, 5s random).
- **Integrity Gate:** Blake2b hashing of 64KB chunks at the start and end of files for stable identification.
- **BLAKE2B Hashing Strategy:** 3-point sampling (Start 64KB + Middle 64KB + End 64KB).
- **Extraction Metrics:**
  - **SNR:** RMS-based noise floor detection (10th percentile blocks).
  - **True Peak Detection:** Implemented ITU-R BS.1770 for clipping detection.
  - **Nyquist Aliasing Detection:** Added to spectral analysis.
  - **Clipping:** Sample amplitude ≥ 0.98 Full Scale.
  - **Spectral Roll-Off:** Sample-rate adaptive, formula: threshold = 0.95 * (sample_rate / 2).
  - **Phase Correlation:** Mid-Side energy ratio as primary detector and IACC (Inter-Aural Cross-Correlation) to corroborate only if file doubtful.
  - **Crackling Density:** Second-order derivative analysis, Zero-crossing rate spikes, Impulse response correlation so use Audacity's click removal algorithm as a crackling detector.

---

## 5. ML Sentinel (Random Forest Brain)
- **Inference:** Uses a `RandomForestRegressor` loaded from versioned `.pkl` artifacts via `joblib`.
- **Incremental Learning:** Offline retrainer processes human-corrected data from SQLite.
- **Atomic Persistence:** Uses a "write-then-swap" strategy for weight files in the `weights/` directory to prevent corruption during save operations.
- **CPU Fallback:** Graceful degradation to CPU-based LLM inference if GPU is unavailable.

---

## 6. Conditional LLM Arbitration
- **Trigger Condition:** Arbitration is invoked only for the "gray zone" where the suspicion score is between **0.4 and 0.7**.
- **Operational Fallback:** If the LLM service is unreachable, the system reverts to the primary ML verdict immediately.
- **Determinism:** Decisions are logged with model names, prompts, and timestamps to ensure reproducibility.

---

## 7. Persistence & Audit (SQLite)
- **WAL Mode:** Enabled for concurrent read/write performance.
- **Resource Tracking:** The system monitors **SQLite WAL file growth** to prevent disk bloating.
- **Forensic Audit:** All high-risk actions (deletions, status changes, AI interventions) are recorded in a mandatory **`audit.csv`** file.
- **Thread Safety:** Every worker obtains its own thread-local connection from the repository factory.
- **WAL File Growth Tracking:** Monitor SQLite WAL file growth to prevent disk bloating.
- **Duplicate Detection Hash I/O Monitoring:** Early warning for disk I/O saturation.

---

## 8. Resource Management & Telemetry
A 5+ year maintenance horizon requires high visibility into system health:
- **`psutil` Tracking:** Real-time monitoring of CPU usage, RAM saturation (>85% warning), and Disk I/O MB/s.
- **GPU/VRAM Monitoring:** Monitoring VRAM usage via `nvidia-smi` (with planned ROCM/OpenCL support).
- **Log Segregation:**
  - `system.log`: Startup, health checks, and infrastructure errors.
  - `analysis.log`: Detailed DSP and pipeline telemetry.
  - `ml_llm.log`: Inference outcomes and arbitration traces.
- **GPU/VRAM Monitoring:** Support for AMD (ROCM) and Intel GPU (planned).
- **OpenCL/ROCM Support:** Planned for future GPU acceleration.

---

## 9. Operational Guarantees
- **Clear Shutdown:** Sequence: Cancel workers → Terminate LLM tasks → Close DB connections.
- **Fail-Closed Posture:** If pre-flight diagnostics fail, the UI remains in an inactive state to protect library integrity.
- **Scalability:** Optimized hash I/O and segmented loading allow for 3900x faster processing than full-file analysis.
- **Numerical Stability:** Use `librosa.cache(level=40)` to avoid redundant STFT computations.
- **Floating Point Precision:** Consider `float64` for feature extraction.
- **Loudness Normalization Detection:** EBU R128 / ReplayGain detection via `pyloudnorm`.

