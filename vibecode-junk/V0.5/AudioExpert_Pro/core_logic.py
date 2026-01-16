import json, os
from PySide6.QtCore import QObject, QThreadPool
from ui.view import AudioExpertView
from analyzer import AudioAnalyzer
from model import FraudModel
from services.llm_service import LLMService
from workers import AnalysisWorker

class AudioExpertApp(QObject):
    def __init__(self):
        super().__init__()
        self.config = json.load(open("config.json"))
        self.analyzer = AudioAnalyzer(self.config)
        self.model = FraudModel(self.config)
        self.llm = LLMService(self.config)
        self.threadpool = QThreadPool()
        self.view = AudioExpertView(self.config)
        
        self.view.scan_requested.connect(self.dispatch_analysis)
        self.view.feedback_given.connect(self.model.update_feedback)

    def dispatch_analysis(self, path):
        worker = AnalysisWorker(path, self.analyzer, self.model, self.llm)
        worker.signals.dsp_ready.connect(self.view.handle_dsp_ready)
        worker.signals.result.connect(self.view.handle_analysis_result)
        self.threadpool.start(worker)

    def run(self):
        self.view.show()

