"""
Analyseur de qualité audio avec interface graphique PySide6
Détecte les craquements, clipping, bruit de fond dans des fichiers audio
Permet l'écoute et l'apprentissage basé sur les retours utilisateur
Détection de doublons et fichiers vides

Installation des dépendances:
pip install librosa soundfile numpy scipy requests pygame mutagen PySide6

Pour le LLM local, installez Ollama:
https://ollama.ai/
Puis: ollama pull llama2
"""

import os
import sys
import json
import librosa
import soundfile as sf
import numpy as np
from scipy import signal
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import hashlib

# Interface graphique
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, QProgressBar,
    QTableWidget, QTableWidgetItem, QTabWidget, QGroupBox, QSpinBox,
    QCheckBox, QMessageBox, QSplitter, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor

# Pour lire les métadonnées audio
try:
    from mutagen import File as MutagenFile
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False

# Pour la lecture audio
try:
    import pygame
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    AUDIO_PLAYBACK_AVAILABLE = False


# ============================================================================
# CLASSES BACKEND (identiques à la version console)
# ============================================================================

class DuplicateDetector:
    """Détecteur de fichiers en double"""
    def __init__(self):
        self.duplicates_by_hash = {}
        self.duplicates_by_name = {}
        self.duplicates_by_tags = {}
        self.empty_files = []
        
    def calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return None
    
    def get_audio_metadata(self, file_path: str) -> Optional[Dict]:
        if not METADATA_AVAILABLE:
            return None
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio is None:
                return None
            metadata = {
                'artist': audio.get('artist', [None])[0] if audio.get('artist') else None,
                'title': audio.get('title', [None])[0] if audio.get('title') else None,
                'album': audio.get('album', [None])[0] if audio.get('album') else None,
            }
            return metadata
        except Exception:
            return None
    
    def analyze_files(self, file_paths: List[str], progress_callback=None) -> Dict:
        total = len(file_paths)
        for i, file_path in enumerate(file_paths, 1):
            if progress_callback:
                progress_callback(i, total)
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                self.empty_files.append(file_path)
                continue
            
            basename = os.path.basename(file_path).lower()
            if basename not in self.duplicates_by_name:
                self.duplicates_by_name[basename] = []
            self.duplicates_by_name[basename].append(file_path)
            
            file_hash = self.calculate_file_hash(file_path)
            if file_hash:
                if file_hash not in self.duplicates_by_hash:
                    self.duplicates_by_hash[file_hash] = []
                self.duplicates_by_hash[file_hash].append(file_path)
            
            metadata = self.get_audio_metadata(file_path)
            if metadata and metadata['artist'] and metadata['title']:
                tag_key = (
                    metadata['artist'].lower() if metadata['artist'] else '',
                    metadata['title'].lower() if metadata['title'] else ''
                )
                if tag_key != ('', ''):
                    if tag_key not in self.duplicates_by_tags:
                        self.duplicates_by_tags[tag_key] = []
                    self.duplicates_by_tags[tag_key].append(file_path)
        
        hash_duplicates = {k: v for k, v in self.duplicates_by_hash.items() if len(v) > 1}
        name_duplicates = {k: v for k, v in self.duplicates_by_name.items() if len(v) > 1}
        tag_duplicates = {k: v for k, v in self.duplicates_by_tags.items() if len(v) > 1}
        
        return {
            'empty_files': self.empty_files,
            'duplicates_by_hash': hash_duplicates,
            'duplicates_by_name': name_duplicates,
            'duplicates_by_tags': tag_duplicates,
            'stats': {
                'empty_files_count': len(self.empty_files),
                'hash_duplicate_groups': len(hash_duplicates),
                'hash_duplicate_files': sum(len(v) for v in hash_duplicates.values()),
                'name_duplicate_groups': len(name_duplicates),
                'name_duplicate_files': sum(len(v) for v in name_duplicates.values()),
                'tag_duplicate_groups': len(tag_duplicates),
                'tag_duplicate_files': sum(len(v) for v in tag_duplicates.values()),
            }
        }


class LearningDatabase:
    """Base de données pour l'apprentissage"""
    def __init__(self, db_file: str = "audio_learning_db.json"):
        self.db_file = db_file
        self.data = self.load()
    
    def load(self) -> Dict:
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'training_samples': [],
            'statistics': {'total_reviewed': 0, 'defective': 0, 'good': 0}
        }
    
    def save(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, indent=2, ensure_ascii=False, fp=f)
    
    def add_sample(self, file_data: Dict, user_label: str, user_comment: str = ""):
        sample = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'file': file_data['file'],
            'path': file_data['path'],
            'metrics': {k: v for k, v in file_data.items() if k not in ['file', 'path']},
            'user_label': user_label,
            'user_comment': user_comment
        }
        self.data['training_samples'].append(sample)
        self.data['statistics']['total_reviewed'] += 1
        self.data['statistics'][user_label] += 1
        self.save()


class AudioPlayer:
    """Lecteur audio"""
    def __init__(self):
        if AUDIO_PLAYBACK_AVAILABLE:
            pygame.mixer.init()
        self.playing = False
    
    def play(self, file_path: str):
        if not AUDIO_PLAYBACK_AVAILABLE:
            return False
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            self.playing = True
            return True
        except Exception:
            return False
    
    def stop(self):
        if AUDIO_PLAYBACK_AVAILABLE:
            pygame.mixer.music.stop()
            self.playing = False
    
    def is_playing(self):
        if AUDIO_PLAYBACK_AVAILABLE:
            return pygame.mixer.music.get_busy()
        return False


class AudioQualityAnalyzer:
    """Analyseur de qualité audio"""
    def __init__(self, llm_url: str = "http://localhost:11434/api/generate", 
                 llm_model: str = "llama2"):
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.learning_db = LearningDatabase()
        self.audio_player = AudioPlayer()
        
    def analyze_audio_file(self, file_path: str) -> Dict:
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return {
                    'file': os.path.basename(file_path),
                    'path': file_path,
                    'file_size': 0,
                    'quality_score': 0,
                    'defect_type': 'empty_file',
                    'auto_classified': 'defective'
                }
            
            y, sr = librosa.load(file_path, sr=None, mono=True)
            duration = librosa.get_duration(y=y, sr=sr)
            
            clipping_ratio = np.sum(np.abs(y) > 0.99) / len(y)
            signal_power = np.mean(y ** 2)
            noise_estimate = np.median(np.abs(y))
            snr = 10 * np.log10(signal_power / (noise_estimate ** 2 + 1e-10))
            
            diff = np.diff(y)
            threshold = np.std(diff) * 3
            crackling_count = np.sum(np.abs(diff) > threshold)
            crackling_rate = crackling_count / len(diff)
            
            zcr = np.mean(librosa.zero_crossings(y))
            crest_factor = np.max(np.abs(y)) / (np.sqrt(np.mean(y ** 2)) + 1e-10)
            
            score = 100.0
            score -= clipping_ratio * 1000
            score -= max(0, (20 - snr) * 2)
            score -= crackling_rate * 500
            score -= max(0, (zcr - 0.1) * 100)
            quality_score = max(0, min(100, round(score, 2)))
            
            return {
                'file': os.path.basename(file_path),
                'path': file_path,
                'file_size': file_size,
                'duration': round(duration, 2),
                'sample_rate': sr,
                'clipping_ratio': round(clipping_ratio * 100, 3),
                'snr_db': round(snr, 2),
                'crackling_rate': round(crackling_rate * 1000, 3),
                'zero_crossing_rate': round(zcr, 4),
                'crest_factor': round(crest_factor, 2),
                'quality_score': quality_score
            }
        except Exception as e:
            return {
                'file': os.path.basename(file_path),
                'path': file_path,
                'error': str(e)
            }
    
    def query_llm(self, prompt: str) -> str:
        try:
            payload = {"model": self.llm_model, "prompt": prompt, "stream": False}
            response = requests.post(self.llm_url, json=payload, timeout=120)
            result = response.json()
            return result.get('response', '')
        except Exception as e:
            return f"ERREUR LLM: {str(e)}"


# ============================================================================
# THREADS POUR OPÉRATIONS LONGUES
# ============================================================================

class AnalysisThread(QThread):
    """Thread pour l'analyse audio"""
    progress = Signal(int, int)  # current, total
    finished = Signal(list)  # results
    
    def __init__(self, analyzer, file_paths):
        super().__init__()
        self.analyzer = analyzer
        self.file_paths = file_paths
    
    def run(self):
        results = []
        total = len(self.file_paths)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(self.analyzer.analyze_audio_file, fp): fp 
                for fp in self.file_paths
            }
            
            completed = 0
            for future in as_completed(future_to_file):
                results.append(future.result())
                completed += 1
                self.progress.emit(completed, total)
        
        self.finished.emit(results)


class DuplicateDetectionThread(QThread):
    """Thread pour la détection de doublons"""
    progress = Signal(int, int)
    finished = Signal(dict)
    
    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
    
    def run(self):
        detector = DuplicateDetector()
        results = detector.analyze_files(
            self.file_paths,
            lambda current, total: self.progress.emit(current, total)
        )
        self.finished.emit(results)


# ============================================================================
# INTERFACE GRAPHIQUE PRINCIPALE
# ============================================================================

class AudioAnalyzerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = AudioQualityAnalyzer()
        self.audio_files = []
        self.analysis_results = []
        self.duplicate_results = None
        self.current_review_index = 0
        
        self.init_ui()
        self.check_llm_connection()
    
    def init_ui(self):
        self.setWindowTitle("Analyseur de Qualité Audio - Interface Graphique")
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Onglets
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Onglet 1: Configuration et Analyse
        self.tab_analysis = QWidget()
        self.tabs.addTab(self.tab_analysis, "📊 Analyse")
        self.setup_analysis_tab()
        
        # Onglet 2: Résultats
        self.tab_results = QWidget()
        self.tabs.addTab(self.tab_results, "📋 Résultats")
        self.setup_results_tab()
        
        # Onglet 3: Doublons
        self.tab_duplicates = QWidget()
        self.tabs.addTab(self.tab_duplicates, "🔍 Doublons")
        self.setup_duplicates_tab()
        
        # Onglet 4: Révision Interactive
        self.tab_review = QWidget()
        self.tabs.addTab(self.tab_review, "🎧 Révision")
        self.setup_review_tab()
        
        # Barre de statut
        self.status_label = QLabel("Prêt")
        main_layout.addWidget(self.status_label)
    
    def setup_analysis_tab(self):
        layout = QVBoxLayout(self.tab_analysis)
        
        # Groupe: Sélection du dossier
        folder_group = QGroupBox("📁 Dossier à analyser")
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit("./audio_samples")
        self.browse_btn = QPushButton("Parcourir...")
        self.browse_btn.clicked.connect(self.browse_folder)
        self.scan_btn = QPushButton("Scanner les fichiers")
        self.scan_btn.clicked.connect(self.scan_files)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.browse_btn)
        folder_layout.addWidget(self.scan_btn)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Statistiques de scan
        self.scan_stats = QLabel("Aucun fichier scanné")
        self.scan_stats.setFont(QFont("Arial", 10))
        layout.addWidget(self.scan_stats)
        
        # Groupe: Options d'analyse
        options_group = QGroupBox("⚙️ Options")
        options_layout = QVBoxLayout()
        
        # Nombre de fichiers à analyser
        files_layout = QHBoxLayout()
        files_layout.addWidget(QLabel("Nombre de fichiers à analyser:"))
        self.num_files_spin = QSpinBox()
        self.num_files_spin.setRange(1, 100000)
        self.num_files_spin.setValue(100)
        files_layout.addWidget(self.num_files_spin)
        self.analyze_all_cb = QCheckBox("Analyser tous les fichiers")
        files_layout.addWidget(self.analyze_all_cb)
        files_layout.addStretch()
        options_layout.addLayout(files_layout)
        
        # Nombre de fichiers suspects
        suspects_layout = QHBoxLayout()
        suspects_layout.addWidget(QLabel("Nombre de fichiers suspects à identifier:"))
        self.num_suspects_spin = QSpinBox()
        self.num_suspects_spin.setRange(1, 100)
        self.num_suspects_spin.setValue(10)
        suspects_layout.addWidget(self.num_suspects_spin)
        suspects_layout.addStretch()
        options_layout.addLayout(suspects_layout)
        
        # Détection de doublons
        self.detect_duplicates_cb = QCheckBox("Détecter les doublons et fichiers vides")
        self.detect_duplicates_cb.setChecked(True)
        options_layout.addWidget(self.detect_duplicates_cb)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Boutons d'action
        action_layout = QHBoxLayout()
        self.start_analysis_btn = QPushButton("▶️ Démarrer l'analyse complète")
        self.start_analysis_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        self.start_analysis_btn.clicked.connect(self.start_analysis)
        self.start_analysis_btn.setEnabled(False)
        action_layout.addWidget(self.start_analysis_btn)
        layout.addLayout(action_layout)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Log d'activité
        log_group = QGroupBox("📝 Journal d'activité")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Statistiques d'apprentissage
        stats = self.analyzer.learning_db.data['statistics']
        learning_info = QLabel(f"📚 Base d'apprentissage: {stats['total_reviewed']} fichiers évalués "
                              f"(Défectueux: {stats['defective']}, Bonne qualité: {stats['good']})")
        learning_info.setFont(QFont("Arial", 10))
        layout.addWidget(learning_info)
        
        layout.addStretch()
    
    def setup_results_tab(self):
        layout = QVBoxLayout(self.tab_results)
        
        # Statistiques
        self.results_stats = QLabel("Aucune analyse effectuée")
        self.results_stats.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.results_stats)
        
        # Tableau des résultats
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Fichier", "Score", "Clipping %", "SNR (dB)", "Craquements", "Durée (s)", "Chemin"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        
        # Boutons d'export
        export_layout = QHBoxLayout()
        self.export_json_btn = QPushButton("💾 Exporter en JSON")
        self.export_json_btn.clicked.connect(self.export_results)
        export_layout.addWidget(self.export_json_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)
    
    def setup_duplicates_tab(self):
        layout = QVBoxLayout(self.tab_duplicates)
        
        # Statistiques
        self.dup_stats = QLabel("Aucune détection effectuée")
        self.dup_stats.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.dup_stats)
        
        # Sélecteur de type de doublons
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type de doublons:"))
        self.dup_type_combo = QComboBox()
        self.dup_type_combo.addItems(["Fichiers vides", "Doublons par hash", "Doublons par nom", "Doublons par tags"])
        self.dup_type_combo.currentIndexChanged.connect(self.display_duplicates)
        type_layout.addWidget(self.dup_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Tableau des doublons
        self.dup_table = QTableWidget()
        self.dup_table.setColumnCount(2)
        self.dup_table.setHorizontalHeaderLabels(["Groupe/Fichier", "Chemin"])
        self.dup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.dup_table)
    
    def setup_review_tab(self):
        layout = QVBoxLayout(self.tab_review)
        
        # Informations du fichier en cours
        self.review_info = QLabel("Aucun fichier à réviser")
        self.review_info.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.review_info)
        
        # Détails du fichier
        details_group = QGroupBox("📊 Détails")
        details_layout = QVBoxLayout()
        self.review_details = QTextEdit()
        self.review_details.setReadOnly(True)
        self.review_details.setMaximumHeight(150)
        details_layout.addWidget(self.review_details)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Contrôles de lecture
        playback_group = QGroupBox("🎵 Lecture")
        playback_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶️ Écouter")
        self.play_btn.clicked.connect(self.play_current_file)
        self.stop_btn = QPushButton("⏹️ Arrêter")
        self.stop_btn.clicked.connect(self.stop_playback)
        playback_layout.addWidget(self.play_btn)
        playback_layout.addWidget(self.stop_btn)
        playback_layout.addStretch()
        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)
        
        # Évaluation
        eval_group = QGroupBox("✅ Évaluation")
        eval_layout = QVBoxLayout()
        
        comment_layout = QHBoxLayout()
        comment_layout.addWidget(QLabel("Commentaire (optionnel):"))
        self.review_comment = QLineEdit()
        comment_layout.addWidget(self.review_comment)
        eval_layout.addLayout(comment_layout)
        
        buttons_layout = QHBoxLayout()
        self.defective_btn = QPushButton("❌ Défectueux")
        self.defective_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        self.defective_btn.clicked.connect(lambda: self.mark_file('defective'))
        self.good_btn = QPushButton("✅ Bonne qualité")
        self.good_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        self.good_btn.clicked.connect(lambda: self.mark_file('good'))
        self.skip_btn = QPushButton("⏭️ Sauter")
        self.skip_btn.clicked.connect(self.skip_file)
        buttons_layout.addWidget(self.defective_btn)
        buttons_layout.addWidget(self.good_btn)
        buttons_layout.addWidget(self.skip_btn)
        eval_layout.addLayout(buttons_layout)
        
        eval_group.setLayout(eval_layout)
        layout.addWidget(eval_group)
        
        # Progression
        self.review_progress = QLabel("0 / 0 fichiers révisés")
        layout.addWidget(self.review_progress)
        
        layout.addStretch()
    
    # ========================================================================
    # MÉTHODES PRINCIPALES
    # ========================================================================
    
    def check_llm_connection(self):
        self.log("🔍 Vérification de la connexion au LLM local...")
        response = self.analyzer.query_llm("Réponds simplement 'OK'")
        if "ERREUR" in response:
            self.log("⚠️ LLM non connecté. Certaines fonctionnalités seront limitées.")
            QMessageBox.warning(self, "LLM non disponible", 
                              "Le LLM local n'est pas disponible.\n\n"
                              "Pour l'installer:\n"
                              "1. Téléchargez Ollama: https://ollama.ai/\n"
                              "2. Lancez: ollama serve\n"
                              "3. Installez un modèle: ollama pull llama2")
        else:
            self.log("✅ LLM connecté avec succès")
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier audio")
        if folder:
            self.folder_input.setText(folder)
    
    def scan_files(self):
        folder = self.folder_input.text()
        if not os.path.exists(folder):
            QMessageBox.warning(self, "Erreur", f"Le dossier '{folder}' n'existe pas.")
            return
        
        self.log(f"🔍 Scan du dossier: {folder}")
        audio_extensions = ['.wav', '.mp3', '.flac', '.wma', '.aac', '.ogg', '.m4a']
        self.audio_files = []
        
        for ext in audio_extensions:
            self.audio_files.extend(Path(folder).rglob(f'*{ext}'))
            self.audio_files.extend(Path(folder).rglob(f'*{ext.upper()}'))
        
        self.audio_files = list(set([str(f) for f in self.audio_files]))
        self.audio_files.sort()
        
        self.scan_stats.setText(f"✅ {len(self.audio_files)} fichiers audio trouvés")
        self.log(f"✅ {len(self.audio_files)} fichiers trouvés")
        self.start_analysis_btn.setEnabled(len(self.audio_files) > 0)
        
        if self.analyze_all_cb.isChecked():
            self.num_files_spin.setValue(len(self.audio_files))
    
    def start_analysis(self):
        if not self.audio_files:
            QMessageBox.warning(self, "Erreur", "Aucun fichier à analyser. Scannez d'abord un dossier.")
            return
        
        # Désactiver les boutons
        self.start_analysis_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        
        # Déterminer le nombre de fichiers à analyser
        if self.analyze_all_cb.isChecked():
            files_to_analyze = self.audio_files
        else:
            num = self.num_files_spin.value()
            files_to_analyze = self.audio_files[:num]
        
        self.log(f"📊 Démarrage de l'analyse de {len(files_to_analyze)} fichiers...")
        
        # Détection de doublons si demandée
        if self.detect_duplicates_cb.isChecked():
            self.log("🔍 Détection de doublons en cours...")
            self.dup_thread = DuplicateDetectionThread(files_to_analyze)
            self.dup_thread.progress.connect(self.update_progress)
            self.dup_thread.finished.connect(self.on_duplicate_detection_finished)
            self.dup_thread.start()
        else:
            self.start_audio_analysis(files_to_analyze)
    
    def on_duplicate_detection_finished(self, results):
        self.duplicate_results = results
        stats = results['stats']
        self.log(f"✅ Détection terminée: {stats['empty_files_count']} fichiers vides, "
                f"{stats['hash_duplicate_groups']} groupes de doublons (hash)")
        self.display_duplicates()
        
        # Passer à l'analyse audio
        if self.analyze_all_cb.isChecked():
            files_to_analyze = self.audio_files
        else:
            num = self.num_files_spin.value()
            files_to_analyze = self.audio_files[:num]
        
        self.start_audio_analysis(files_to_analyze)
    
    def start_audio_analysis(self, files):
        self.log(f"🎵 Analyse audio de {len(files)} fichiers...")
        self.analysis_thread = AnalysisThread(self.analyzer, files)
        self.analysis_thread.progress.connect(self.update_progress)
        self.analysis_thread.finished.connect(self.on_analysis_finished)
        self.analysis_thread.start()
    
    def on_analysis_finished(self, results):
        self.analysis_results = results
        
        # Séparer les résultats
        empty_files = [r for r in results if r.get('auto_classified') == 'defective']
        error_files = [r for r in results if 'error' in r]
        valid_results = [r for r in results if 'error' not in r and r.get('auto_classified') != 'defective']
        
        self.log(f"✅ Analyse terminée: {len(results)} fichiers")
        if empty_files:
            self.log(f"   - {len(empty_files)} fichiers vides (auto-classés défectueux)")
        if error_files:
            self.log(f"   - {len(error_files)} fichiers avec erreurs")
        self.log(f"   - {len(valid_results)} fichiers valides")
        
        # Trier par score de qualité
        valid_results.sort(key=lambda x: x.get('quality_score', 100))
        
        # Afficher les résultats
        self.display_results(empty_files + valid_results)
        
        # Préparer la révision interactive
        num_suspects = self.num_suspects_spin.value()
        self.suspicious_files = (empty_files + valid_results)[:num_suspects]
        self.current_review_index = 0
        self.update_review_display()
        
        # Réactiver les boutons
        self.start_analysis_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        
        # Passer à l'onglet résultats
        self.tabs.setCurrentWidget(self.tab_results)
        
        self.log(f"✅ Analyse complète terminée!")
    
    def display_results(self, results):
        self.results_table.setRowCount(0)
        
        for result in results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(result.get('file', 'N/A')))
            
            score_item = QTableWidgetItem(str(result.get('quality_score', 'N/A')))
            score = result.get('quality_score', 100)
            if score < 50:
                score_item.setBackground(QColor(255, 200, 200))
            elif score < 70:
                score_item.setBackground(QColor(255, 255, 200))
            self.results_table.setItem(row, 1, score_item)
            
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result.get('clipping_ratio', 'N/A'))))
            self.results_table.setItem(row, 3, QTableWidgetItem(str(result.get('snr_db', 'N/A'))))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(result.get('crackling_rate', 'N/A'))))
            self.results_table.setItem(row, 5, QTableWidgetItem(str(result.get('duration', 'N/A'))))
            self.results_table.setItem(row, 6, QTableWidgetItem(result.get('path', 'N/A')))
        
        stats_text = f"📊 {len(results)} fichiers affichés"
        valid = [r for r in results if r.get('quality_score', 0) > 0]
        if valid:
            avg_score = sum(r.get('quality_score', 0) for r in valid) / len(valid)
            stats_text += f" | Score moyen: {avg_score:.1f}/100"
        self.results_stats.setText(stats_text)
    
    def display_duplicates(self):
        if not self.duplicate_results:
            return
        
        self.dup_table.setRowCount(0)
        dup_type = self.dup_type_combo.currentText()
        
        if dup_type == "Fichiers vides":
            files = self.duplicate_results['empty_files']
            for file_path in files:
                row = self.dup_table.rowCount()
                self.dup_table.insertRow(row)
                self.dup_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
                self.dup_table.setItem(row, 1, QTableWidgetItem(file_path))
            stats = f"📦 {len(files)} fichiers vides (0 KB)"
        
        elif dup_type == "Doublons par hash":
            duplicates = self.duplicate_results['duplicates_by_hash']
            for i, (hash_val, files) in enumerate(duplicates.items(), 1):
                # Ligne de groupe
                row = self.dup_table.rowCount()
                self.dup_table.insertRow(row)
                group_item = QTableWidgetItem(f"Groupe {i} ({len(files)} fichiers)")
                group_item.setBackground(QColor(220, 220, 220))
                self.dup_table.setItem(row, 0, group_item)
                self.dup_table.setItem(row, 1, QTableWidgetItem(hash_val[:16] + "..."))
                
                # Fichiers du groupe
                for file_path in files:
                    row = self.dup_table.rowCount()
                    self.dup_table.insertRow(row)
                    self.dup_table.setItem(row, 0, QTableWidgetItem(f"  → {os.path.basename(file_path)}"))
                    self.dup_table.setItem(row, 1, QTableWidgetItem(file_path))
            
            stats = self.duplicate_results['stats']
            stats = f"🔐 {stats['hash_duplicate_groups']} groupes | {stats['hash_duplicate_files']} fichiers"
        
        elif dup_type == "Doublons par nom":
            duplicates = self.duplicate_results['duplicates_by_name']
            for i, (name, files) in enumerate(duplicates.items(), 1):
                row = self.dup_table.rowCount()
                self.dup_table.insertRow(row)
                group_item = QTableWidgetItem(f"{name} ({len(files)} fichiers)")
                group_item.setBackground(QColor(220, 220, 220))
                self.dup_table.setItem(row, 0, group_item)
                self.dup_table.setItem(row, 1, QTableWidgetItem(""))
                
                for file_path in files:
                    row = self.dup_table.rowCount()
                    self.dup_table.insertRow(row)
                    self.dup_table.setItem(row, 0, QTableWidgetItem(f"  → {os.path.basename(file_path)}"))
                    self.dup_table.setItem(row, 1, QTableWidgetItem(file_path))
            
            stats = self.duplicate_results['stats']
            stats = f"📝 {stats['name_duplicate_groups']} groupes | {stats['name_duplicate_files']} fichiers"
        
        else:  # Doublons par tags
            duplicates = self.duplicate_results['duplicates_by_tags']
            for i, ((artist, title), files) in enumerate(duplicates.items(), 1):
                row = self.dup_table.rowCount()
                self.dup_table.insertRow(row)
                group_item = QTableWidgetItem(f"{artist} - {title} ({len(files)} fichiers)")
                group_item.setBackground(QColor(220, 220, 220))
                self.dup_table.setItem(row, 0, group_item)
                self.dup_table.setItem(row, 1, QTableWidgetItem(""))
                
                for file_path in files:
                    row = self.dup_table.rowCount()
                    self.dup_table.insertRow(row)
                    self.dup_table.setItem(row, 0, QTableWidgetItem(f"  → {os.path.basename(file_path)}"))
                    self.dup_table.setItem(row, 1, QTableWidgetItem(file_path))
            
            stats = self.duplicate_results['stats']
            stats = f"🏷️ {stats['tag_duplicate_groups']} groupes | {stats['tag_duplicate_files']} fichiers"
        
        self.dup_stats.setText(stats)
    
    def update_review_display(self):
        if not hasattr(self, 'suspicious_files') or not self.suspicious_files:
            self.review_info.setText("Aucun fichier à réviser")
            return
        
        if self.current_review_index >= len(self.suspicious_files):
            self.review_info.setText("✅ Révision terminée!")
            QMessageBox.information(self, "Révision terminée", 
                                   "Vous avez terminé la révision de tous les fichiers suspects.")
            return
        
        file_data = self.suspicious_files[self.current_review_index]
        
        self.review_info.setText(f"Fichier {self.current_review_index + 1}/{len(self.suspicious_files)}: {file_data['file']}")
        
        details = f"Chemin: {file_data['path']}\n"
        details += f"Score qualité: {file_data.get('quality_score', 'N/A')}/100\n"
        
        if file_data.get('auto_classified') == 'defective':
            details += f"Type: Fichier vide (0 KB)\n"
            details += f"Statut: Auto-classé comme DÉFECTUEUX\n"
        else:
            details += f"Durée: {file_data.get('duration', 'N/A')}s\n"
            details += f"Clipping: {file_data.get('clipping_ratio', 'N/A')}%\n"
            details += f"SNR: {file_data.get('snr_db', 'N/A')} dB\n"
            details += f"Craquements: {file_data.get('crackling_rate', 'N/A')}\n"
        
        self.review_details.setText(details)
        self.review_progress.setText(f"{self.current_review_index} / {len(self.suspicious_files)} fichiers révisés")
    
    def play_current_file(self):
        if not hasattr(self, 'suspicious_files') or self.current_review_index >= len(self.suspicious_files):
            return
        
        file_data = self.suspicious_files[self.current_review_index]
        
        if file_data.get('auto_classified') == 'defective':
            QMessageBox.warning(self, "Impossible", "Ce fichier est vide et ne peut pas être lu.")
            return
        
        if self.analyzer.audio_player.play(file_data['path']):
            self.log(f"▶️ Lecture: {file_data['file']}")
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de lire ce fichier audio.")
    
    def stop_playback(self):
        self.analyzer.audio_player.stop()
        self.log("⏹️ Lecture arrêtée")
    
    def mark_file(self, label):
        if not hasattr(self, 'suspicious_files') or self.current_review_index >= len(self.suspicious_files):
            return
        
        file_data = self.suspicious_files[self.current_review_index]
        comment = self.review_comment.text()
        
        self.analyzer.learning_db.add_sample(file_data, label, comment)
        
        label_text = "DÉFECTUEUX" if label == 'defective' else "BONNE QUALITÉ"
        self.log(f"✅ {file_data['file']} marqué comme {label_text}")
        
        self.review_comment.clear()
        self.current_review_index += 1
        self.update_review_display()
    
    def skip_file(self):
        if not hasattr(self, 'suspicious_files'):
            return
        
        self.log(f"⏭️ Fichier sauté")
        self.current_review_index += 1
        self.update_review_display()
    
    def export_results(self):
        if not self.analysis_results:
            QMessageBox.warning(self, "Erreur", "Aucun résultat à exporter.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exporter les résultats", 
            f"audio_analysis_{time.strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            output_data = {
                'analysis_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_files_analyzed': len(self.analysis_results),
                'results': self.analysis_results,
                'learning_statistics': self.analyzer.learning_db.data['statistics']
            }
            
            if self.duplicate_results:
                output_data['duplicate_detection'] = self.duplicate_results['stats']
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.log(f"💾 Résultats exportés: {filename}")
            QMessageBox.information(self, "Export réussi", f"Résultats sauvegardés dans:\n{filename}")
    
    def update_progress(self, current, total):
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Progression: {current}/{total} fichiers")
    
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Style moderne
    
    window = AudioAnalyzerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()