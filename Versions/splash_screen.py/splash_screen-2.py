import requests
from PySide6.QtWidgets import QSplashScreen
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

class SplashScreen(QSplashScreen):
    def __init__(self, config):
        pix = QPixmap(500, 250); pix.fill(QColor("#0F111A"))
        super().__init__(pix)
        self.api = config['llm']['api_url'].replace('/generate', '/tags')

    def run_checks(self):
        self.showMessage("VÉRIFICATION SYSTÈME...", Qt.AlignCenter, Qt.cyan)
        try:
            requests.get(self.api, timeout=2); return True
        except: return False

