import sys
import os
import json
from PySide6.QtWidgets import QApplication, QFileDialog, QTableWidgetItem, QMessageBox
from PySide6.QtCore import QThread, Signal
import numpy as np
import librosa

# Import des modules locaux
from model import AudioModel
from analyzer import AudioAnalyzer, DuplicateEngine
from view import MainView

class ScanWorker(QThread):
    """Thread dédié à l'analyse pour ne pas bloquer l'interface graphique"""
    progress_file = Signal(dict)
    log_msg = Signal(str)
    finished = Signal()

    def __init__(self, folder, config):
        super().__init__()
        self.folder = folder
        self.config = config

    def run(self):
        ana = AudioAnalyzer()
        extensions = self.config['audio']['extensions']
        
        # Liste tous les fichiers
        files = []
        for root, _, fs in os.walk(self.folder):
            for f in fs:
                if any(f.lower().endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, f))

        for f_path in files:
            self.log_msg.emit(f"Analyse de : {os.path.basename(f_path)}")
            
            # 1. Vérification préliminaire (0kb / Inaccessible)
            if os.path.getsize(f_path) == 0:
                data = {
                    'path': f_path, 'hash': 'N/A', 'clipping': 0, 'snr': 0,
                    'crackling': 0, 'roll_off': 0, 'score': 0, 'ml_score': 1.0,
                    'tag': 'ban', 'tags_info': 'Fichier vide (0kb)', 'timestamp': 0
                }
            else:
                try:
                    # 2. Analyse du signal
                    metrics = ana.get_metrics(f_path)
                    metrics.update({
                        'path': f_path,
                        'hash': ana.get_hash(f_path),
                        'tags_info': ana.get_tags(f_path),
                        'ml_score': 0.0, # Sera calculé par le modèle après
                        'tag': None
                    })
                    data = metrics
                except Exception as e:
                    # 3. Gestion des fichiers corrompus (Non décodables)
                    data = {
                        'path': f_path, 'hash': 'ERR', 'clipping': 0, 'snr': 0,
                        'crackling': 0, 'roll_off': 0, 'score': 0, 'ml_score': 1.0,
                        'tag': 'ban', 'tags_info': f"Erreur décodage: {str(e)}", 'timestamp': 0
                    }
            
            self.progress_file.emit(data)
        
        self.finished.emit()

class AudioController:
    def __init__(self):
        # Chargement config
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            
        self.model = AudioModel(self.config['paths']['db_name'])
        self.view = MainView()
        self.current_analysis_results = []

        # Connexions des signaux de la vue
        self.view.btn_browse.clicked.connect(self.start_scan)
        self.view.btn_good.clicked.connect(lambda: self.label_file("Bon"))
        self.view.btn_bad.clicked.connect(lambda: self.label_file("Défectueux"))
        
        # Sélection dans le tableau pour afficher la Waveform
        self.view.table.itemSelectionChanged.connect(self.load_selected_file_to_review)

    def start_scan(self):
        folder = QFileDialog.getExistingDirectory(self.view, "Sélectionner le dossier audio")
        if folder:
            self.view.log.append(f"🚀 Démarrage du scan : {folder}")
            self.view.table.setRowCount(0)
            self.current_analysis_results = []
            
            self.thread = ScanWorker(folder, self.config)
            self.thread.progress_file.connect(self.on_file_done)
            self.thread.log_msg.connect(lambda m: self.view.log.append(m))
            self.thread.finished.connect(self.on_scan_finished)
            self.thread.start()

    def on_file_done(self, data):
        # Calcul du score ML si le modèle est prêt
        if self.model.is_trained:
            features = [[data['clipping'], data['snr'], data['crackling'], data['roll_off']]]
            data['ml_score'] = float(self.model.classifier.predict_proba(features)[0][1])
        
        self.model.save_analysis(data)
        self.current_analysis_results.append(data)
        
        # Mise à jour du tableau
        row = self.view.table.rowCount()
        self.view.table.insertRow(row)
        self.view.table.setItem(row, 0, QTableWidgetItem(os.path.basename(data['path'])))
        self.view.table.setItem(row, 1, QTableWidgetItem(f"{data['score']:.1f}"))
        self.view.table.setItem(row, 2, QTableWidgetItem(f"{data['ml_score']:.2f}"))
        self.view.table.setItem(row, 4, QTableWidgetItem(data['tag'] or ""))

    def on_scan_finished(self):
        self.view.log.append("✅ Analyse terminée.")
        QMessageBox.information(self.view, "Succès", "Le scan du dossier est terminé.")

    def load_selected_file_to_review(self):
        """Affiche la Waveform du fichier sélectionné dans l'onglet révision"""
        row = self.view.table.currentRow()
        if row < 0: return
        
        file_data = self.current_analysis_results[row]
        self.view.lbl_current.setText(f"Révision : {os.path.basename(file_data['path'])}")
        
        # Génération Waveform
        try:
            y, sr = librosa.load(file_data['path'], sr=None, duration=30)
            self.view.ax.clear()
            self.view.ax.plot(np.linspace(0, len(y)/sr, len(y)), y, color='#1f77b4', alpha=0.7)
            
            # Marqueur d'erreur si présent
            if file_data['timestamp'] > 0:
                self.view.ax.axvline(x=file_data['timestamp'], color='red', linestyle='--', label='Défaut détecté')
            
            self.view.ax.set_facecolor('#f0f0f0')
            self.view.canvas.draw()
        except Exception as e:
            self.view.log.append(f"Impossible d'afficher la waveform : {e}")

    def label_file(self, label):
        """Apprentissage incrémental lors de la validation utilisateur"""
        row = self.view.table.currentRow()
        if row < 0: return
        
        path = self.current_analysis_results[row]['path']
        # Mise à jour en DB
        with self.model.conn_context() as conn: # Utilise le manager de model.py
            conn.execute("UPDATE audio_data SET label=? WHERE path=?", (label, path))
        
        self.view.log.append(f"Apprentissage : {os.path.basename(path)} marqué {label}")
        
        # Ré-entraînement flash
        if self.model.train_ml():
            self.view.log.append("🔄 Modèle ML mis à jour avec succès.")

    def ask_llm_arbitration(self, suspicious_files):
    """
    Envoie les 5 fichiers les plus suspects au LLM pour une analyse croisée.
    """
    # Préparation du rapport de données pour le LLM
    report = "Analyse ces données audio et identifie les priorités de révision :\n"
    for f in suspicious_files:
        report += f"- {os.path.basename(f['path'])}: Clipping={f['clipping']:.2%}, SNR={f['snr']:.1f}dB, Score={f['score']:.1f}/100\n"

    prompt_system = (
            "Tu es un ingénieur du son expert en restauration audio. "
            "Voici les données techniques de fichiers suspects. "
            "Analyse-les et dis-moi lequel est le plus endommagé et pourquoi\n\n"
        )
    prompt = {
        "model": self.config['ia']['model_name'],
        "prompt": prompt_system + f"{report}\nRéponds brièvement : quel fichier semble le plus critique et pourquoi ?",
        "stream": False
    }

    try:
        self.view.log.append("🤖 Consultation de l'expert IA pour arbitrage...")
        response = requests.post(self.config['ia']['llm_url'], json=prompt, timeout=15)
        if response.status_code == 200:
            verdict = response.json().get('response', 'Pas de réponse')
            self.view.log.append(f"✨ Verdict IA : {verdict}")
        else:
            self.view.log.append("⚠️ Le LLM n'a pas pu répondre (Vérifiez si Ollama tourne).")
    except Exception as e:
        self.view.log.append(f"❌ Erreur de connexion LLM : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AudioController()
    controller.view.show()
    sys.exit(app.exec())
