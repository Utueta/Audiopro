"""
Audiopro v0.3.1
Handles the orchestration of analysis results and LLM arbitration routing.
- Implementation: Gray-zone logic [0.35 - 0.75] for automated AI triage.
"""
from .brain.random_forest import AudioBrain
from .models import AnalysisResult
from services.llm_interface import LLMProvider

class SystemManager:
    def __init__(self, llm_service: LLMProvider = None):
        self.brain = AudioBrain()
        self.llm = llm_service

    def route_analysis(self, dsp_data: dict) -> AnalysisResult:
        """
        Orchestrates the transition from DSP to Intelligence.
        Uses Suspicion Score to determine if LLM arbitration is required.
        """
        verdict, score = self.brain.classify(dsp_data)
        justification = "Local RF Classification"
        llm_involved = False
        
        # Trigger LLM only for gray-zone [0.35 - 0.75] per ARCHITECTURE.md
        if 0.35 <= score <= 0.75 and self.llm:
            llm_involved = True
            verdict, justification = self.llm.arbitrate(dsp_data)
            
        return AnalysisResult(
            verdict=verdict,
            score=score,
            justification=justification,
            llm_involved=llm_involved
        )
