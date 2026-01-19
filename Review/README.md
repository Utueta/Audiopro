# Audiopro Industrial: Expert Audit & Library Cleaning System

**Version:** 0.2.5 (Industrial Consolidated)  
**Architecture:** Asynchronous Hexagonal Pipeline  
**Target Environment:** Linux/Windows (CUDA-enabled)

---

## 1. System Overview

Audiopro is a professional-grade audio analysis tool designed for large-scale library cleaning. It replaces subjective listening with deterministic DSP metrics, local Machine Learning classification, and conditional LLM arbitration.

### Key Capabilities
* **Deterministic DSP:** Objective SNR, Clipping, and Spectral Integrity analysis.
* **Local ML Intelligence:** Persistent Random Forest classification for rapid sorting.
* **AI Arbitration:** Ambiguity resolution using Qwen 2.5 via Ollama.
* **Industrial UI:** Deep Obsidian Dark interface with real-time GPU/VRAM telemetry.

---

## 2. Technical Architecture

The system follows a strict **Separation of Concerns** to ensure that high-load audio analysis never blocks the user interface or hardware monitoring.



### Core Components
* **Orchestrator (`manager.py`):** Routes data between UI signals and background workers.
* **DSP Engine (`pipeline.py`):** Stateless feature extraction using Librosa/NumPy.
* **Intelligence (`random_forest.py`):** Thread-safe ML inference using local weights.
* **Persistence (`repository.py`):** High-concurrency SQLite storage with WAL mode enabled.

---

## 3. Installation & Bootloader

### Prerequisites
1.  **Python 3.10+**
2.  **NVIDIA GPU** with latest drivers (Required for Telemetry and ML acceleration).
3.  **Ollama:** Installed and running locally with the `qwen2.5` model.

### Setup
```bash
# Clone the repository
git clone [https://github.com/user/audiopro-industrial.git](https://github.com/user/audiopro-industrial.git)
cd audiopro-industrial

# Initialize Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt
