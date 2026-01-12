from PySide6.QtCore import QRunnable, QObject, Signal, Slot
import traceback

class WorkerSignals(QObject):
    """
    Définit les signaux disponibles pour le thread d'analyse.
    - result: Transmet le dictionnaire complet (DSP + ML)
    - error: Transmet un tuple (Exception, Message String)
    - progress: Transmet un entier pour la barre de progression
    """
    result = Signal(dict)
    error = Signal(str)
    progress = Signal(int)

class AnalysisWorker(QRunnable):
    """
    Worker chargé d'exécuter le pipeline d'analyse pour UN fichier.
    Hérite de QRunnable pour être géré par le QThreadPool d'app.py.
    """
    def __init__(self, manager, file_path):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        """
        Point d'entrée du thread. Exécute le pipeline du CentralManager.
        """
        try:
            # Appel du pipeline consolidé (Pre-scan -> DSP -> ML)
            # Cette méthode dans manager.py intègre déjà la sécurité RAM
            analysis_data = self.manager.process_file(self.file_path)
            
            # Injection du chemin pour que la vue sache quel fichier mettre à jour
            if isinstance(analysis_data, dict):
                analysis_data['path'] = self.file_path
                
                # Émission du résultat vers le thread principal (UI)
                self.signals.result.emit(analysis_data)
            
        except Exception as e:
            # Capture complète de l'erreur pour le debug senior
            error_msg = f"Erreur sur {self.file_path}: {str(e)}"
            self.signals.error.emit(error_msg)
            print(traceback.format_exc())
