"""
Audiopro v0.3.1
Handles the orchestration of analysis results and LLM arbitration routing.
"""
from .brain.random_forest import AudioBrain
from .models import AnalysisResult

class SystemManager:
    def __init__(self):
        self.brain = AudioBrain()

    def route_analysis(self, dsp_data: dict) -> AnalysisResult:
        """Orchestrates the transition from DSP to Intelligence."""
        verdict, score = self.brain.classify(dsp_data)
        
        # Trigger LLM only for gray-zone [0.35 - 0.75]
        llm_status = "Skipped"
        if 0.35 <= score <= 0.75:
            llm_status = "Pending Arbitration"
            
        return AnalysisResult(
            verdict=verdict,
            score=score,
            llm_involved=(llm_status != "Skipped")
        )
