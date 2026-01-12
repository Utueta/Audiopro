import sys, multiprocessing
from PySide6.QtWidgets import QApplication
from core_logic import AudioExpertApp

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    core = AudioExpertApp()
    core.run()
    sys.exit(app.exec())

