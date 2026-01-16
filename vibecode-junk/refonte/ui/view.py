import os
import logging
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTableWidget, 
                             QTableWidgetItem, QProgressBar, QLabel, QTextEdit,
                             QHeaderView, QAbstractItemView, QMenu, QMessageBox)
from PySide6.QtCore import Qt, Slot, Signal, QThread, QUrl, QFileInfo
from PySide6.QtGui import QDesktopServices, QAction
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# --- WORKER THREAD POUR L'ANALYSE ---
class AnalysisWorker(QThread):
    file_processed = Signal(dict)
    log_msg = Signal(str)
    ai_status = Signal(str)
    progress_update = Signal(int)
    finished = Signal()

    def __init__(self, manager, folder_path):
        super().__init__()
        self.manager = manager
        self.folder_path = folder_path

    def run(self):
        files_to_scan = []
        for root, _, files in os.walk(self.folder_path):
            for f in files:
                if f.lower().endswith(('.wav', '.flac', '.mp3')):
                    files_to_scan.append(os.path.join(root, f))
        
        for i, path in enumerate(files_to_scan):
            self.log_msg.emit(f"Traitement : {os.path.basename(path)}")
            
            # On indique à l'UI que l'IA peut être sollicitée
            self.ai_status.emit("thinking")
            result = self.manager.process_file(path)
            self.ai_status.emit("idle")
            
            self.file_processed.emit(result)
            self.progress_update.emit(i + 1)
        
        self.finished.emit()

# --- VUE PRINCIPALE ---
class AudioExpertView(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Audio Expert Pro V2.6 - Obsidian Cleaner")
        self.resize(1300, 900)
        self._apply_theme()
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.tab_scan = QWidget()
        self.tab_results = QWidget()
        self.tab_revision = QWidget()
        
        self.tabs.addTab(self.tab_scan, "🚀 SCAN")
        self.tabs.addTab(self.tab_results, "📊 RÉSULTATS")
        self.tabs.addTab(self.tab_revision, "🔍 RÉVISION")
        
        self._setup_scan_tab()
        self._setup_results_tab()
        self._setup_revision_tab()

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f0f; }
            QTabWidget::pane { border: 1px solid #333; background: #0f0f0f; }
            QTabBar::tab { background: #1a1a1a; color: #777; padding: 12px 20px; }
            QTabBar::tab:selected { background: #0f0f0f; color: #00f2ff; border-bottom: 2px solid #00f2ff; }
            QPushButton { background-color: #00f2ff; color: #000; font-weight: bold; border-radius: 2px; }
            QTableWidget { background-color: #141414; color: #ddd; gridline-color: #222; font-size: 11px; }
            QHeaderView::section { background-color: #1a1a1a; color: #00f2ff; border: 1px solid #222; }
            QTextEdit { background-color: #050505; color: #00ff41; font-family: 'Consolas'; border: 1px solid #222; }
            QProgressBar { border: 1px solid #222; background: #111; text-align: center; }
            QProgressBar::chunk { background-color: #00f2ff; }
        """)

    def _setup_scan_tab(self):
        layout = QVBoxLayout(self.tab_scan)
        
        header = QHBoxLayout()
        self.ai_status_lbl = QLabel("● IA EN ATTENTE")
        self.ai_status_lbl.setStyleSheet("color: #444; font-weight: bold;")
        header.addStretch()
        header.addWidget(self.ai_status_lbl)
        layout.addLayout(header)

        self.btn_select = QPushButton("DÉMARRER L'ANALYSE D'UN DOSSIER")
        self.btn_select.setFixedHeight(60)
        self.btn_select.clicked.connect(self._open_folder_dialog)
        
        self.progress_bar = QProgressBar()
        self.console_log = QTextEdit()
        self.console_log.setReadOnly(True)
        
        layout.addWidget(self.btn_select)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.console_log)

    def _setup_results_tab(self):
        layout = QVBoxLayout(self.tab_results)
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(["Fichier", "Clipping", "Score ML", "Verdict", "Détails IA"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Activation du clic droit
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.results_table)

    def _setup_revision_tab(self):
        layout = QHBoxLayout(self.tab_revision)
        self.revision_list = QTableWidget(0, 1)
        self.revision_list.setHorizontalHeaderLabels(["Sélectionner pour Analyse Visuelle"])
        self.revision_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.revision_list.cellClicked.connect(self.on_revision_item_selected)
        layout.addWidget(self.revision_list, 1)
        
        viz_layout = QVBoxLayout()
        self.figure, (self.ax_wave, self.ax_spec) = plt.subplots(2, 1, figsize=(5, 8))
        self.figure.patch.set_facecolor('#0f0f0f')
        self.canvas = FigureCanvas(self.figure)
        viz_layout.addWidget(self.canvas)
        layout.addLayout(viz_layout, 2)

    # --- LOGIQUE DE CONTEXTE (CLIC DROIT) ---
    def show_context_menu(self, position):
        item = self.results_table.itemAt(position)
        if not item: return
        row = item.row()

        menu = QMenu(self)
        menu.setStyleSheet("background-color: #1a1a1a; color: #eee; border: 1px solid #333;")
        
        act_open = menu.addAction("📂 Ouvrir le dossier")
        act_del = menu.addAction("❌ Supprimer définitivement")
        act_del.setStyleSheet("color: #ff4444;")

        action = menu.exec(self.results_table.viewport().mapToGlobal(position))
        
        path = self.results_table.item(row, 0).data(Qt.UserRole)
        if not path: return

        if action == act_open:
            folder = QFileInfo(path).absoluteDir().absolutePath()
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        
        elif action == act_del:
            self.confirm_delete_file(path, row)

    def confirm_delete_file(self, path, row):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmation de suppression")
        msg.setText(f"Voulez-vous vraiment supprimer ce fichier ?\n\n{os.path.basename(path)}")
        msg.setInformativeText("Cette action est irréversible.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setIcon(QMessageBox.Warning)
        
        if msg.exec() == QMessageBox.Yes:
            try:
                os.remove(path)
                self.results_table.removeRow(row)
                self.console_log.append(f"🗑️ Supprimé : {path}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de supprimer le fichier : {e}")

    # --- SLOTS ET THREADS ---
    def _open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir dossier")
        if folder:
            self._start_worker(folder)

    def _start_worker(self, folder):
        self.btn_select.setEnabled(False)
        self.results_table.setRowCount(0)
        self.worker = AnalysisWorker(self.manager, folder)
        self.worker.file_processed.connect(self.update_results)
        self.worker.log_msg.connect(lambda m: self.console_log.append(f">> {m}"))
        self.worker.ai_status.connect(self._update_ai_status)
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.finished.connect(lambda: self.btn_select.setEnabled(True))
        
        # Calcul du max pour la barre
        count = sum([len(files) for r, d, files in os.walk(folder) if any(f.lower().endswith(('.wav','.mp3','.flac')) for f in files)])
        self.progress_bar.setMaximum(count)
        self.worker.start()

    def _update_ai_status(self, status):
        if status == "thinking":
            self.ai_status_lbl.setText("● IA QWEN ANALYSE...")
            self.ai_status_lbl.setStyleSheet("color: #00f2ff;")
        else:
            self.ai_status_lbl.setText("● IA EN ATTENTE")
            self.ai_status_lbl.setStyleSheet("color: #444;")

    @Slot(dict)
    def update_results(self, data):
        if data.get('status') == "ERROR": return
        
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        path = data.get('path', '')
        name = QTableWidgetItem(os.path.basename(path))
        name.setData(Qt.UserRole, path) # Chemin stocké ici
        self.results_table.setItem(row, 0, name)
        
        dsp = data.get('dsp', {})
        self.results_table.setItem(row, 1, QTableWidgetItem(f"{dsp.get('clipping', 0):.2f}%"))
        
        score = data.get('score', 0)
        item_score = QTableWidgetItem(f"{score:.2f}")
        if score > 0.7: item_score.setForeground(Qt.red)
        self.results_table.setItem(row, 2, item_score)
        
        self.results_table.setItem(row, 3, QTableWidgetItem(data.get('final_decision', '')))
        
        llm = data.get('llm_analysis', {})
        self.results_table.setItem(row, 4, QTableWidgetItem(llm.get('reason', 'Auto')))

        # Ajout révision
        rev_row = self.revision_list.rowCount()
        self.revision_list.insertRow(rev_row)
        item_rev = QTableWidgetItem(os.path.basename(path))
        item_rev.setData(Qt.UserRole, path)
        self.revision_list.setItem(rev_row, 0, item_rev)

    def on_revision_item_selected(self, row, col):
        path = self.revision_list.item(row, 0).data(Qt.UserRole)
        if path:
            y, sr = self.manager.dsp_engine.load_audio_safely(path)
            times, wave, spec = self.manager.dsp_engine.get_visual_data(y, sr)
            self.draw_visuals(times, wave, spec)

    def draw_visuals(self, times, waveform, spectrogram):
        self.ax_wave.clear()
        self.ax_spec.clear()
        self.ax_wave.plot(times, waveform, color='#00f2ff', linewidth=0.5)
        self.ax_wave.axis('off')
        self.ax_spec.imshow(spectrogram, aspect='auto', origin='lower', cmap='magma')
        self.ax_spec.axis('off')
        self.canvas.draw()
