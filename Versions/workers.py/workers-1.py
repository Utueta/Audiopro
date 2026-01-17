import traceback
import logging
from PySide6.QtCore import QRunnable, QObject, Signal, Slot

class WorkerSignals(QObject):
    """
    Signaux de communication pour le Worker.
    Définit l'interface entre le thread de calcul et l'UI Obsidian.
    """
    # Émis quand l'analyse est réussie (retourne le dictionnaire de résultats)
    result = Signal(dict)
    
    # Émis en cas d'erreur (retourne le message d'erreur)
    error = Signal(str)
    
    # Émis au début et à la fin (utile pour des indicateurs spécifiques)
    finished = Signal()

class AnalysisWorker(QRunnable):
    """
    Worker haute performance pour l'analyse individuelle de fichiers.
    Encapsulé pour être exécuté dans un QThreadPool.
    """
    def __init__(self, manager, file_path):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.signals = WorkerSignals()
        self.logger = logging.getLogger("Audiopro.Worker")
        
        # DevSecOps : Le thread se supprime de la mémoire une fois fini
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        """
        Point d'entrée du thread. Exécute le pipeline de certification.
        """
        try:
            self.logger.info(f"Début de l'analyse : {self.file_path}")
            
            # Appel au Manager (Pipeline : Metadata -> DSP -> Brain -> LLM)
            result = self.manager.process_file(self.file_path)
            
            # Ajout du chemin pour que l'UI sache quel fichier est traité
            if isinstance(result, dict):
                result['path'] = self.file_path
                self.signals.result.emit(result)
            else:
                raise ValueError("Le format de retour du Manager est invalide.")

        except Exception as e:
            # Capture détaillée de l'erreur pour l'audit
            error_msg = f"Erreur sur {self.file_path}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.signals.error.emit(error_msg)
            
        finally:
            self.signals.finished.emit()
