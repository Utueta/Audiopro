"""
Audiopro v0.3.1
Handles the documentation of system threading, data flow, and industrial standards.
"""
# Architecture Overview
[cite_start]The system follows a **Hexagonal Architecture**[cite: 31].

## 1. Threading Model
- **Main Thread:** PySide6 UI responsiveness.
- [cite_start]**Worker Pool:** `QThreadPool` handles heavy DSP and ML[cite: 47].
- **Persistence:** SQLite with thread-local connections and WAL mode.

## 2. Intelligence Layer (v0.3.1 Sentinel)
- **Primary:** Suspicion Score [0.0 - 1.0].
- [cite_start]**Fallback:** 60/40 Heuristic (SNR/Clipping).
- [cite_start]**Arbitration:** LLM triggered only for scores between 0.35 and 0.75[cite: 54].



# ARCHITECTURE.md: Audiopro Industrial Standards

## 1. Visual Flowchart: The Audio Processing Lifecycle
This narrative illustrates the deterministic path of an audio file through the Audiopro architecture, ensuring absolute traceability from system boot to persistent storage.

* **Initialization (The Bootloader):** `app.py` initializes dependency injection and triggers `splash_screen.py`. The system runs `scripts/check_health.py` and `scripts/smi.sh` to verify CUDA and the `ollama_llm.py` service status before the UI appears.
* **Trigger (The Orchestrator):** When a user selects a file in `view.py`, the `manager.py` coordinates the handoff. It instantiates a `QRunnable` in `workers.py` to move the task off the Main Thread.
* **Audio Processing Engine:** Inside the background thread, `core/analyzer/pipeline.py` serves as the entry point, calling `dsp.py` (RMS/Clipping) and `spectral.py` (Frequency analysis) to extract raw features.
* **Intelligence & Arbitrage:** Raw features are passed to `core/brain/random_forest.py` for local ML classification using weights from `core/brain/weights/`. Simultaneously, `services/ollama_llm.py` performs asynchronous AI arbitration.
* **Output & Persistence:** Results are packaged into `models.py` data contracts. `persistence/repository.py` secures the record in `database/audiopro_v03.db` via WAL mode, while `view.py` updates the `gauges.py` and `graphs.py` components.
* **Infrastructure Control:** `config.json` provides the global parameters for thresholds and file paths across all layers.



---

## 2. Threading Model & Concurrency Safety
To maintain the "Expert Audit Interface" responsiveness, the Main Thread (GUI) is strictly reserved for user interaction and widget rendering.

### The Worker Pattern (QRunnable)
All heavy DSP, ML inference, and LLM calls must be offloaded using the `core/workers.py` infrastructure.
* **Explicit Thread Affinity:** Workers must not access `ui/` components directly. 
* **Signal-Based Communication:** Results must be returned to the Main Thread via Qt Signals (using `Qt.QueuedConnection`) to ensure thread-safe UI updates.
* **No Shared Mutable State:** Data must be passed into workers as immutable objects (Data Contracts) from `core/models.py`.
* **Affinity Verification:** Thread affinity is enforced at object creation and verified in debug builds using `moveToThread()`.



### Async/Qt Integration
For asynchronous services like `ollama_llm.py`:
* **Event Loop Bridge:** Use a dedicated bridge (e.g., `qasync`) or run the `asyncio` loop in a managed background thread to prevent blocking the PySide6 event loop.
* **Cancellation Tokens:** Every pipeline execution must support a cancellation signal to allow immediate resource release during user-initiated stops or app shutdown.

---

## 3. Persistence & Data Integrity
The system uses SQLite via `persistence/repository.py` for deterministic data storage.

### SQLite Multi-Threaded Access
* **Connection Scoping:** Each `QRunnable` worker must request its own short-lived connection from the repository factory to avoid cross-thread crashes.
* **WAL Mode (Write-Ahead Logging):** Enabled for optimal concurrency, allowing simultaneous reads and writes.
    ```sql
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    ```
* **Database Structure:** Migrations and schema versioning are strictly handled via `persistence/schema.py`. Main tables include `analysis_results`, `classifications`, and `audio_metadata`.
* **Atomic Weight Persistence:** `brain/random_forest.py` must use a "write-then-swap" strategy for `.pkl` files in the `weights/` directory to prevent corruption during save operations.

---

## 4. Resource Management & Traceability
A 5+ year maintenance horizon requires high visibility into failures.

* **Memory-Scoped Analysis:** `analyzer/pipeline.py` must ensure audio buffers are cleared immediately after feature extraction to prevent unbounded memory growth.
* **Graceful Shutdown Sequence:** 1. `manager.py` signals all active `workers.py` tasks to cancel.
    2. Asynchronous LLM loops are terminated with specific timeouts.
    3. Repository closes connection pools only after worker completion signals are received.
* **Log Segregation:** * `logs/analysis.log`: Detailed DSP and pipeline telemetry.
    * `logs/system.log`: Critical infrastructure, I/O errors, and LLM arbitration traces.
* **Pre-flight Health Checks:** `scripts/check_health.py` and `scripts/smi.sh` are executed at startup to validate CUDA and service health.

---

## 5. Maintenance & Evolution
* **No Unnecessary Complexity:** Every change must be justified by an industrial need.
* **Mandatory Documentation:** Any modification must be documented in `ARCHITECTURE.md` and `RELEASE_NOTES.md`.
* **Mandatory Tests:** No merge without validation via the `Pytest` suite and reproduction fixtures.
