# ARCHITECTURE.md: Audiopro Industrial Standards

## 1. Threading Model & Concurrency Safety
[cite_start]To maintain the "Expert Audit Interface" responsiveness, the Main Thread (GUI) is strictly reserved for user interaction and widget rendering[cite: 16]. 

### The Worker Pattern (QRunnable)
[cite_start]All heavy DSP, ML inference, and LLM calls must be offloaded using the `core/workers.py` infrastructure[cite: 13].
* **Explicit Thread Affinity**: Workers must not access `ui/` components directly. 
* [cite_start]**Signal-Based Communication**: Results must be returned to the Main Thread via Qt Signals to ensure thread-safe UI updates[cite: 13].
* [cite_start]**No Shared Mutable State**: Data must be passed into workers as immutable objects (Data Contracts) from `core/models.py`[cite: 10].



### Async/Qt Integration
[cite_start]For asynchronous services like `ollama_llm.py`[cite: 15]:
* **Event Loop Bridge**: Use a dedicated bridge (e.g., `qasync`) or run the `asyncio` loop in a managed background thread to prevent blocking the PySide6 event loop.
* [cite_start]**Cancellation Tokens**: Every pipeline execution must support a cancellation signal to allow immediate resource release during user-initiated stops or app shutdown[cite: 11].

---

## 2. Persistence & Data Integrity
[cite_start]The system uses SQLite via `persistence/repository.py` for deterministic data storage[cite: 14].

### SQLite Multi-Threaded Access
* **Connection Scoping**: SQLite connections are not thread-safe. [cite_start]Each `QRunnable` worker must request its own short-lived connection from the repository factory[cite: 14].
* [cite_start]**WAL Mode (Write-Ahead Logging)**: Must be enabled to allow concurrent reads (UI/Gauges) while the background worker writes analysis results[cite: 14].
    ```sql
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    ```
* **Atomic Weight Persistence**: `brain/random_forest.py` must use a "write-then-swap" strategy for `.pkl` files in the `weights/` directory to prevent corruption[cite: 12, 13].

---

## 3. Memory & Resource Management
* [cite_start]**Memory-Scoped Analysis**: The `analyzer/pipeline.py` must ensure audio buffers are cleared immediately after feature extraction to prevent unbounded memory growth during batch processing[cite: 11].
* [cite_start]**Lifecycle Management**: The `core/manager.py` (Orchestrator) is responsible for the graceful shutdown of the LLM pool and the database connection pool before the process exits[cite: 13, 14].

---

## 4. Traceability & Diagnostics
[cite_start]A 5+ year maintenance horizon requires high visibility into failures[cite: 18].
* **Log Segregation**: 
    * [cite_start]`logs/analysis.log`: Detailed DSP and pipeline telemetry[cite: 18].
    * [cite_start]`logs/system.log`: Critical infrastructure, I/O errors, and LLM arbitration traces[cite: 18].
* [cite_start]**Pre-flight Health Checks**: The `scripts/check_health.py` must be executed at startup to validate CUDA availability and service health (Ollama/FFmpeg)[cite: 21].
