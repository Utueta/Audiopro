#"""
# Audiopro v0.3.1
# - Handles orchestration of DSP → ML → conditional LLM → persistence under hexagonal rules.
#"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Optional, Union

from core.analyzer.pipeline import AudioAnalysisPipeline
from core.brain.model_interface import AudioQualityModel  # Protocol / abstract
from persistence.repository import AnalysisRepository     # Thread-scoped connections enforced there
from services.llm_interface import LLMProvider            # Protocol / abstract
from core.models import AnalysisResult

logger = logging.getLogger("system.manager")


class AnalysisManager:
    """Core orchestrator.

    Hexagonal rules:
      - No UI imports.
      - No sqlite3 usage here (persistence via repository only).
      - All dependencies injected (testability + boundary integrity).
      - Thread-safety: stateless per call, no shared DB connections.

    Arbitration policy (Spec-review-consolid-up):
      - Deterministic DSP baseline always runs.
      - ML triage runs locally.
      - LLM arbitration only in the gray zone (bounded thresholds).
      - Graceful degradation if LLM/GPU unavailable (AI_FAILED → LOCAL_ONLY behavior).
    """

    def __init__(
        self,
        *,
        dsp_pipeline: AudioAnalysisPipeline,
        ml_model: AudioQualityModel,
        llm_provider: LLMProvider,
        repository: AnalysisRepository,
        threshold_ban: float = 0.80,
        threshold_llm_gray_low: float = 0.40,
        threshold_llm_gray_high: float = 0.70,
    ):
        self._dsp = dsp_pipeline
        self._ml = ml_model
        self._llm = llm_provider
        self._repo = repository

        self._threshold_ban = float(threshold_ban)
        self._gray_low = float(threshold_llm_gray_low)
        self._gray_high = float(threshold_llm_gray_high)

    def audit_file(
        self,
        file_path: Union[str, Path],
        *,
        is_segmented: Optional[bool] = None,
    ) -> AnalysisResult:
        """Deterministic audit pipeline with cache + conditional arbitration.

        Steps:
          1) DSP pipeline emits AnalysisResult contract (hash + metrics + provenance)
          2) Cache by file_hash (if present, return persisted result)
          3) ML inference enriches contract
          4) Conditional LLM arbitration in gray-zone only
          5) Final decision + persistence (thread-scoped repository)

        Notes:
          - `is_segmented` is a per-call override from UI; if None, pipeline uses config default.
        """
        p = Path(file_path)

        # Phase 1: DSP + provenance (includes file_hash)
        base: AnalysisResult = self._dsp.analyze_file(str(p), is_segmented=is_segmented)

        # Phase 1b: Cache check (by file_hash)
        cached = self._repo.get_by_hash(base.file_hash)
        if cached is not None:
            logger.info("Cache hit: %s (%s)", p.name, base.file_hash)
            return cached

        # Phase 2: ML inference (local, deterministic for fixed model artifacts)
        ml_out = self._ml.predict(base)  # expects full contract input
        result = replace(
            base,
            ml_classification=str(getattr(ml_out, "predicted_class", "PENDING")),
            ml_confidence=float(getattr(ml_out, "confidence", 0.0)),
        )

        # Phase 3: Conditional LLM arbitration (gray-zone)
        # We gate primarily on suspicion_score for cross-version stability.
        score = float(result.suspicion_score)

        llm_involved = False
        arbitration_status = "LOCAL_ONLY"  # LOCAL_ONLY, AI_ARBITRATED, AI_FAILED
        llm_verdict = None
        llm_justification = None

        if self._gray_low <= score <= self._gray_high:
            llm_involved = True
            arbitration_status = "AI_ARBITRATED"
            try:
                llm_out = self._llm.arbitrate(result)
                llm_verdict = getattr(llm_out, "verdict", None) or getattr(llm_out, "recommendation", None)
                llm_justification = getattr(llm_out, "justification", None) or getattr(llm_out, "reasoning", None)
            except Exception as e:
                arbitration_status = "AI_FAILED"
                # Degrade gracefully: keep local verdict, capture operational trace
                logger.exception("LLM arbitration failure for %s: %s", p.name, e)

        # Phase 4: Final decision logic
        final_class = result.ml_classification

        # If LLM produced a usable verdict, allow override (policy-level decision)
        if llm_verdict:
            final_class = str(llm_verdict)
        else:
            # Deterministic ban threshold based on suspicion score
            if score >= self._threshold_ban:
                final_class = "BAN"
            elif final_class == "PENDING":
                final_class = "GOOD"

        final = replace(
            result,
            ml_classification=final_class,
            llm_involved=llm_involved,
            llm_verdict=llm_verdict,
            llm_justification=llm_justification,
            arbitration_status=arbitration_status,
        )

        # Phase 5: Persistence (repository enforces thread-scoped connections and WAL mode)
        self._repo.record_result(final)

        return final

