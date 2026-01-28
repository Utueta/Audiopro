import sys
import os
import json
import sqlite3
import hashlib
import numpy as np
import librosa
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QLabel, QProgressBar, 
                             QTableWidget, QTableWidgetItem, QTextEdit, QSpinBox, QCheckBox,
                             QHeaderView, QMessageBox, QComboBox)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from sklearn.ensemble import RandomForestClassifier

# ===================== MOTEUR LOGIQUE (DB & ML) =====================
class AudioLogic:
    def __init__(self):
        self.db_path = "audio_history.db"
        self._init_db()
        self.model = RandomForestClassifier(n_estimators=100)
        self.trained = False
        self.retrain()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT UNIQUE, 
                hash_128 TEXT, clipping REAL, snr REAL, crackling REAL, 
                quality_score REAL, ml_score REAL, label TEXT, tag TEXT, 
                error_ts REAL, file_size INTEGER, duration REAL)""")

    def retrain(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT clipping, snr, crackling, quality_score, label FROM history WHERE label IS NOT NULL")
            rows = cursor.fetchall()
            if rows and len(set(r[4] for r in rows)) > 1:
                X = [r[:4] for r in rows]
                y = [1 if r[4] == 'Défectueux' else 0 for r in rows]
                self.model.fit(X, y)
                self.trained = True

# ===================== THREAD D'ANALYSE =====================
class AnalysisWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(list)

    def __init__(self, folder, count, detect_dups, logic):
        super().__init__()
        self.folder = folder
        self.count = count
        self.detect_dups = detect_dups
        self.logic = logic

    def run(self):
        files = []
        for r, _, fs in os.walk(self.folder):
            for f in fs:
                if f.lower().endswith(('.wav', '.mp3', '.flac', '.m4a')):
                    files.append(os.path.join(r, f))
        
        files = files[:self.count] if self.count > 0 else files
        results = []
        
        for i, path in enumerate(files):
            self.log.emit(f"Analyse : {os.path.basename(path)}")
            res = self.analyze_file(path)
            results.append(res)
            self.progress.emit(int((i+1)/len(files)*100))
        
        self.finished.emit(results)

    def analyze_file(self, path):
        # Simplicité pour l'exemple (reprend la logique V2.2)
        try:
            size = os.path.getsize(path)
            if size == 0: return {"file_path": path, "quality_score": 0, "tag": "ban", "ml_score": 1.0}
            y, sr = librosa.load(path, sr=None, duration=10)
            clipping = float(np.sum(np.abs(y) >= 0.98) / len(y))
            # Score simplifié
            q_score = 100 - (clipping * 100)
            return {"file_path": path, "quality_score": q_score, "clipping": clipping, "ml_score": 0.5}
        except:
            return {"file_path": path, "quality_score": 0, "tag": "ban", "ml_score": 1.0}

# ===================== INTERFACE GRAPHIQUE =====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Expert Studio V3")
        self.resize(1100, 800)
        self.logic = AudioLogic()
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.init_analysis_tab()
        self.init_results_tab()
        self.init_duplicate_tab()
        self.init_review_tab()

    # --- ONGLET 1 : ANALYSE ---
    def init_analysis_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Folder Selection
        f_layout = QHBoxLayout()
        self.path_edit = QTextEdit("./audio_samples")
        self.path_edit.setMaximumHeight(30)
        btn_browse = QPushButton("Parcourir")
        btn_browse.clicked.connect(self.browse_folder)
        f_layout.addWidget(self.path_edit)
        f_layout.addWidget(btn_browse)
        
        # Config
        c_layout = QHBoxLayout()
        self.spin_count = QSpinBox(); self.spin_count.setRange(0, 10000); self.spin_count.setValue(100)
        self.check_dups = QCheckBox("Détecter Doublons")
        c_layout.addWidget(QLabel("Fichiers :")); c_layout.addWidget(self.spin_count)
        c_layout.addWidget(self.check_dups)
        
        self.btn_start = QPushButton("Lancer l'Analyse")
        self.btn_start.clicked.connect(self.start_analysis)
        self.progress = QProgressBar()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        
        layout.addLayout(f_layout)
        layout.addLayout(c_layout)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.progress)
        layout.addWidget(self.log_area)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "📊 Analyse")

    # --- ONGLET 2 : RÉSULTATS ---
    def init_results_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Fichier", "Qualité", "ML Score", "Tag"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        
        btn_export = QPushButton("Exporter en JSON")
        btn_export.clicked.connect(self.export_json)
        
        layout.addWidget(self.table)
        layout.addWidget(self.canvas)
        layout.addWidget(btn_export)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "📋 Résultats")

    # --- ONGLET 3 : DOUBLONS ---
    def init_duplicate_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        self.combo_dup = QComboBox()
        self.combo_dup.addItems(["Par Hash", "Par Nom", "Par Tags", "Fichiers Vides"])
        self.dup_list = QTableWidget(0, 3)
        self.dup_list.setHorizontalHeaderLabels(["Sélection", "Chemin", "Type"])
        btn_del = QPushButton("Supprimer la sélection")
        btn_del.setStyleSheet("background-color: #ff4444; color: white;")
        
        layout.addWidget(QLabel("Type de doublons :"))
        layout.addWidget(self.combo_dup)
        layout.addWidget(self.dup_list)
        layout.addWidget(btn_del)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🔍 Doublons")

    # --- ONGLET 4 : RÉVISION ---
    def init_review_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.lbl_file = QLabel("Aucun fichier sélectionné")
        self.lbl_file.setWordWrap(True)
        self.lbl_file.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Audio Player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        btn_play = QPushButton("▶ Écouter l'erreur")
        btn_play.clicked.connect(self.play_audio)
        
        # Buttons
        b_layout = QHBoxLayout()
        btn_bad = QPushButton("❌ Défectueux"); btn_bad.clicked.connect(lambda: self.tag_file("Défectueux"))
        btn_good = QPushButton("✅ Bonne qualité"); btn_good.clicked.connect(lambda: self.tag_file("Bon"))
        btn_skip = QPushButton("⏭️ Sauter"); btn_skip.clicked.connect(self.next_review)
        b_layout.addWidget(btn_bad); b_layout.addWidget(btn_good); b_layout.addWidget(btn_skip)
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("Commentaire optionnel...")
        self.comment_edit.setMaximumHeight(60)
        
        layout.addWidget(self.lbl_file)
        layout.addWidget(btn_play)
        layout.addWidget(QLabel("Commentaire :"))
        layout.addWidget(self.comment_edit)
        layout.addLayout(b_layout)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🎧 Révision")

    # --- LOGIQUE ---
    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier")
        if path: self.path_edit.setText(path)

    def start_analysis(self):
        self.btn_start.setEnabled(False)
        self.log_area.clear()
        self.worker = AnalysisWorker(self.path_edit.toPlainText(), self.spin_count.value(), self.check_dups.isChecked(), self.logic)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(lambda m: self.log_area.append(m))
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, results):
        self.btn_start.setEnabled(True)
        self.current_results = results
        self.update_results_table(results)
        self.update_chart(results)
        QMessageBox.information(self, "Terminé", f"Analyse finie : {len(results)} fichiers.")

    def update_results_table(self, results):
        self.table.setRowCount(len(results))
        for i, r in enumerate(results):
            score = r.get('quality_score', 0)
            name_item = QTableWidgetItem(os.path.basename(r['file_path']))
            score_item = QTableWidgetItem(f"{score:.1f}")
            
            # Code Couleur
            if score < 50: score_item.setBackground(Qt.red)
            elif score < 70: score_item.setBackground(Qt.yellow)
            
            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, score_item)
            self.table.setItem(i, 2, QTableWidgetItem(f"{r.get('ml_score', 0):.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(r.get('tag', '')))

    def update_chart(self, results):
        scores = [r['quality_score'] for r in results]
        ax = self.canvas.figure.subplots()
        ax.clear()
        ax.hist(scores, bins=10, color='skyblue', edgecolor='black')
        ax.set_title("Distribution des scores de qualité")
        self.canvas.draw()

    def tag_file(self, label):
        # Logique d'enregistrement et passage au suivant
        self.log_area.append(f"Fichier marqué comme {label}")
        self.next_review()

    def play_audio(self):
        # Simulé ici, nécessite un fichier valide chargé
        pass

    def next_review(self):
        # Logique de passage au fichier suivant dans la liste
        pass

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder", "", "JSON Files (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(self.current_results, f)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
