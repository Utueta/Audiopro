import requests
from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

class SplashScreen(QSplashScreen):
    def __init__(self, config):
        pixmap = QPixmap(400, 220)
        pixmap.fill(QColor("#0F111A"))
        super().__init__(pixmap)
        self.config = config

    def run_checks(self):
        self.showMessage("SANTÉ SYSTÈME...", Qt.AlignCenter, Qt.white)
        try:
            requests.get(self.config['llm']['api_url'].replace('/generate', '/tags'), timeout=2)
            return True
        except:
            return False
