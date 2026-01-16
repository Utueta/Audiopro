"""
Analyseur de qualité audio avec interaction LLM local et apprentissage
Détecte les craquements, clipping, bruit de fond dans des fichiers audio
Permet l'écoute et l'apprentissage basé sur les retours utilisateur
Détection de doublons et fichiers vides

Installation des dépendances:
pip install librosa soundfile numpy scipy requests pygame mutagen

Pour le LLM local, installez Ollama:
https://ollama.ai/
Puis: ollama pull llama2
"""

import os
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

# Pour lire les métadonnées audio
try:
    from mutagen import File as MutagenFile
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False
    print("⚠️  mutagen non installé. Détection de doublons par tags désactivée.")
    print("   Installez avec: pip install mutagen")

# Pour la lecture audio
try:
    import pygame
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    AUDIO_PLAYBACK_AVAILABLE = False
    print("⚠️  pygame non installé. Lecture audio désactivée.")
    print("   Installez avec: pip install pygame")


class DuplicateDetector:
    """
    Détecteur de fichiers en double (par hash, nom, et métadonnées)
    """
    def __init__(self):
        self.duplicates_by_hash = {}  # hash -> [liste de fichiers]
        self.duplicates_by_name = {}  # nom -> [liste de fichiers]
        self.duplicates_by_tags = {}  # (artiste, titre) -> [liste de fichiers]
        self.empty_files = []
        
    def calculate_file_hash(self, file_path: str, chunk_size: int = 8192) -> str:
        """
        Calcule le hash SHA256 d'un fichier
        
        Args:
            file_path: Chemin du fichier
            chunk_size: Taille des chunks pour la lecture
            
        Returns:
            Hash SHA256 du fichier
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            return None
    
    def get_audio_metadata(self, file_path: str) -> Optional[Dict]:
        """
        Extrait les métadonnées audio (tags ID3, etc.)
        
        Returns:
            Dictionnaire avec artiste, titre, album
        """
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
    
    def analyze_files(self, file_paths: List[str]) -> Dict:
        """
        Analyse les fichiers pour détecter les doublons et fichiers vides
        
        Returns:
            Dictionnaire avec les résultats de détection
        """
        print("\n🔍 Détection de doublons et fichiers vides...")
        
        total = len(file_paths)
        for i, file_path in enumerate(file_paths, 1):
            if i % 50 == 0 or i == total:
                print(f"   Progression: {i}/{total} fichiers analysés", end='\r')
            
            # Vérifier si le fichier est vide
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                self.empty_files.append(file_path)
                continue
            
            # Détection par nom de fichier (basename)
            basename = os.path.basename(file_path).lower()
            if basename not in self.duplicates_by_name:
                self.duplicates_by_name[basename] = []
            self.duplicates_by_name[basename].append(file_path)
            
            # Détection par hash (plus lent mais précis)
            file_hash = self.calculate_file_hash(file_path)
            if file_hash:
                if file_hash not in self.duplicates_by_hash:
                    self.duplicates_by_hash[file_hash] = []
                self.duplicates_by_hash[file_hash].append(file_path)
            
            # Détection par métadonnées (tags)
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
        
        print()  # Nouvelle ligne après progression
        
        # Filtrer pour ne garder que les vrais doublons (2+ fichiers)
        hash_duplicates = {k: v for k, v in self.duplicates_by_hash.items() if len(v) > 1}
        name_duplicates = {k: v for k, v in self.duplicates_by_name.items() if len(v) > 1}
        tag_duplicates = {k: v for k, v in self.duplicates_by_tags.items() if len(v) > 1}
        
        results = {
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
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """
        Génère un rapport détaillé des doublons et fichiers vides
        """
        report = "=" * 70 + "\n"
        report += "RAPPORT DE DÉTECTION - DOUBLONS ET FICHIERS VIDES\n"
        report += "=" * 70 + "\n\n"
        
        stats = results['stats']
        
        # Fichiers vides
        report += f"📦 FICHIERS VIDES (0 KB): {stats['empty_files_count']}\n"
        if results['empty_files']:
            report += "   Ces fichiers seront automatiquement classés comme défectueux.\n\n"
            for i, file_path in enumerate(results['empty_files'][:20], 1):
                report += f"   {i}. {file_path}\n"
            if len(results['empty_files']) > 20:
                report += f"   ... et {len(results['empty_files']) - 20} autres\n"
        report += "\n"
        
        # Doublons par hash (identiques bit à bit)
        report += f"🔐 DOUBLONS PAR HASH (fichiers identiques): {stats['hash_duplicate_groups']} groupes, {stats['hash_duplicate_files']} fichiers\n"
        if results['duplicates_by_hash']:
            report += "   Ces fichiers sont EXACTEMENT identiques (même contenu).\n\n"
            for i, (hash_val, files) in enumerate(list(results['duplicates_by_hash'].items())[:5], 1):
                report += f"   Groupe {i} ({len(files)} fichiers):\n"
                for file_path in files:
                    report += f"      - {file_path}\n"
                report += "\n"
            if len(results['duplicates_by_hash']) > 5:
                report += f"   ... et {len(results['duplicates_by_hash']) - 5} autres groupes\n"
        report += "\n"
        
        # Doublons par nom
        report += f"📝 DOUBLONS PAR NOM: {stats['name_duplicate_groups']} groupes, {stats['name_duplicate_files']} fichiers\n"
        if results['duplicates_by_name']:
            report += "   Ces fichiers ont le même nom (mais peuvent être dans des dossiers différents).\n\n"
            for i, (name, files) in enumerate(list(results['duplicates_by_name'].items())[:5], 1):
                report += f"   Groupe {i}: {name} ({len(files)} fichiers)\n"
                for file_path in files[:3]:
                    report += f"      - {file_path}\n"
                if len(files) > 3:
                    report += f"      ... et {len(files) - 3} autres\n"
                report += "\n"
            if len(results['duplicates_by_name']) > 5:
                report += f"   ... et {len(results['duplicates_by_name']) - 5} autres groupes\n"
        report += "\n"
        
        # Doublons par tags
        if METADATA_AVAILABLE and results['duplicates_by_tags']:
            report += f"🏷️  DOUBLONS PAR TAGS (artiste/titre): {stats['tag_duplicate_groups']} groupes, {stats['tag_duplicate_files']} fichiers\n"
            report += "   Ces fichiers ont les mêmes métadonnées (artiste + titre).\n\n"
            for i, ((artist, title), files) in enumerate(list(results['duplicates_by_tags'].items())[:5], 1):
                report += f"   Groupe {i}: {artist} - {title} ({len(files)} fichiers)\n"
                for file_path in files[:3]:
                    report += f"      - {file_path}\n"
                if len(files) > 3:
                    report += f"      ... et {len(files) - 3} autres\n"
                report += "\n"
            if len(results['duplicates_by_tags']) > 5:
                report += f"   ... et {len(results['duplicates_by_tags']) - 5} autres groupes\n"
        
        return report


class LearningDatabase:
    """
    Base de données pour stocker les retours utilisateur et améliorer les prédictions
    """
    def __init__(self, db_file: str = "audio_learning_db.json"):
        self.db_file = db_file
        self.data = self.load()
    
    def load(self) -> Dict:
        """Charge la base de données existante"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'training_samples': [],
            'statistics': {
                'total_reviewed': 0,
                'defective': 0,
                'good': 0
            }
        }
    
    def save(self):
        """Sauvegarde la base de données"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, indent=2, ensure_ascii=False, fp=f)
    
    def add_sample(self, file_data: Dict, user_label: str, user_comment: str = ""):
        """Ajoute un échantillon avec le retour utilisateur"""
        sample = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'file': file_data['file'],
            'path': file_data['path'],
            'metrics': {
                'quality_score': file_data['quality_score'],
                'clipping_ratio': file_data['clipping_ratio'],
                'snr_db': file_data['snr_db'],
                'crackling_rate': file_data['crackling_rate'],
                'zero_crossing_rate': file_data['zero_crossing_rate'],
                'crest_factor': file_data['crest_factor']
            },
            'user_label': user_label,  # 'defective' ou 'good'
            'user_comment': user_comment
        }
        
        self.data['training_samples'].append(sample)
        self.data['statistics']['total_reviewed'] += 1
        self.data['statistics'][user_label] += 1
        self.save()
    
    def get_training_summary(self) -> str:
        """Génère un résumé des données d'apprentissage"""
        samples = self.data['training_samples']
        if not samples:
            return "Aucune donnée d'apprentissage disponible."
        
        stats = self.data['statistics']
        summary = f"Base d'apprentissage: {stats['total_reviewed']} fichiers évalués\n"
        summary += f"  - Défectueux: {stats['defective']}\n"
        summary += f"  - Bonne qualité: {stats['good']}\n\n"
        
        # Calculer les moyennes par catégorie
        defective = [s for s in samples if s['user_label'] == 'defective']
        good = [s for s in samples if s['user_label'] == 'good']
        
        if defective:
            avg_def = {
                'quality_score': np.mean([s['metrics']['quality_score'] for s in defective]),
                'clipping_ratio': np.mean([s['metrics']['clipping_ratio'] for s in defective]),
                'snr_db': np.mean([s['metrics']['snr_db'] for s in defective]),
                'crackling_rate': np.mean([s['metrics']['crackling_rate'] for s in defective])
            }
            summary += "Moyennes fichiers DÉFECTUEUX:\n"
            summary += f"  Score qualité: {avg_def['quality_score']:.2f}\n"
            summary += f"  Clipping: {avg_def['clipping_ratio']:.3f}%\n"
            summary += f"  SNR: {avg_def['snr_db']:.2f} dB\n"
            summary += f"  Craquements: {avg_def['crackling_rate']:.3f}\n\n"
        
        if good:
            avg_good = {
                'quality_score': np.mean([s['metrics']['quality_score'] for s in good]),
                'clipping_ratio': np.mean([s['metrics']['clipping_ratio'] for s in good]),
                'snr_db': np.mean([s['metrics']['snr_db'] for s in good]),
                'crackling_rate': np.mean([s['metrics']['crackling_rate'] for s in good])
            }
            summary += "Moyennes fichiers BONNE QUALITÉ:\n"
            summary += f"  Score qualité: {avg_good['quality_score']:.2f}\n"
            summary += f"  Clipping: {avg_good['clipping_ratio']:.3f}%\n"
            summary += f"  SNR: {avg_good['snr_db']:.2f} dB\n"
            summary += f"  Craquements: {avg_good['crackling_rate']:.3f}\n"
        
        return summary


class AudioPlayer:
    """
    Lecteur audio simple utilisant pygame
    """
    def __init__(self):
        if AUDIO_PLAYBACK_AVAILABLE:
            pygame.mixer.init()
    
    def play(self, file_path: str, duration: Optional[float] = None):
        """
        Joue un fichier audio
        
        Args:
            file_path: Chemin vers le fichier
            duration: Durée max en secondes (None = tout le fichier)
        """
        if not AUDIO_PLAYBACK_AVAILABLE:
            print("⚠️  Lecture audio non disponible (pygame non installé)")
            return
        
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            print(f"▶️  Lecture de: {os.path.basename(file_path)}")
            print("   [Espace] Pause/Reprise | [S] Stop | [Q] Quitter la lecture")
            
            start_time = time.time()
            paused = False
            
            while pygame.mixer.music.get_busy():
                # Vérifier la durée max
                if duration and (time.time() - start_time) > duration:
                    pygame.mixer.music.stop()
                    break
                
                time.sleep(0.1)
            
            pygame.mixer.music.stop()
            
        except Exception as e:
            print(f"❌ Erreur lecture: {e}")
    
    def stop(self):
        """Arrête la lecture"""
        if AUDIO_PLAYBACK_AVAILABLE:
            pygame.mixer.music.stop()


class AudioQualityAnalyzer:
    def __init__(self, llm_url: str = "http://localhost:11434/api/generate", 
                 llm_model: str = "llama2"):
        """
        Initialise l'analyseur audio
        
        Args:
            llm_url: URL de l'API du LLM local (Ollama par défaut)
            llm_model: Nom du modèle LLM à utiliser
        """
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.learning_db = LearningDatabase()
        self.audio_player = AudioPlayer()
        
    def analyze_audio_file(self, file_path: str) -> Dict:
        """
        Analyse un fichier audio et extrait les métriques de qualité
        
        Returns:
            Dictionnaire avec les métriques d'analyse
        """
        try:
            # Vérifier si le fichier est vide
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
            
            # Charger le fichier audio
            y, sr = librosa.load(file_path, sr=None, mono=True)
            
            # Métriques de base
            duration = librosa.get_duration(y=y, sr=sr)
            
            # 1. Détection de clipping (distorsion)
            clipping_ratio = np.sum(np.abs(y) > 0.99) / len(y)
            
            # 2. Ratio signal/bruit (SNR)
            signal_power = np.mean(y ** 2)
            noise_estimate = np.median(np.abs(y))
            snr = 10 * np.log10(signal_power / (noise_estimate ** 2 + 1e-10))
            
            # 3. Détection de craquements (pics soudains)
            diff = np.diff(y)
            threshold = np.std(diff) * 3
            crackling_count = np.sum(np.abs(diff) > threshold)
            crackling_rate = crackling_count / len(diff)
            
            # 4. Zero-crossing rate (indicateur de bruit haute fréquence)
            zcr = np.mean(librosa.zero_crossings(y))
            
            # 5. Crest factor (dynamique)
            crest_factor = np.max(np.abs(y)) / (np.sqrt(np.mean(y ** 2)) + 1e-10)
            
            # 6. Analyse spectrale pour détecter anomalies
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
            
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
                'spectral_centroid': round(spectral_centroid, 2),
                'spectral_rolloff': round(spectral_rolloff, 2),
                'quality_score': self._calculate_quality_score(
                    clipping_ratio, snr, crackling_rate, zcr, crest_factor
                )
            }
        except Exception as e:
            return {
                'file': os.path.basename(file_path),
                'path': file_path,
                'error': str(e)
            }
    
    def _calculate_quality_score(self, clipping: float, snr: float, 
                                 crackling: float, zcr: float, crest: float) -> float:
        """
        Calcule un score de qualité global (0-100)
        """
        score = 100.0
        
        # Pénalités
        score -= clipping * 1000  # Clipping très mauvais
        score -= max(0, (20 - snr) * 2)  # SNR faible = mauvais
        score -= crackling * 500  # Craquements
        score -= max(0, (zcr - 0.1) * 100)  # ZCR élevé = bruit
        
        return max(0, min(100, round(score, 2)))
    
    def analyze_batch(self, file_paths: List[str], max_workers: int = 4) -> List[Dict]:
        """
        Analyse plusieurs fichiers en parallèle
        """
        results = []
        total = len(file_paths)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.analyze_audio_file, fp): fp 
                for fp in file_paths
            }
            
            completed = 0
            for future in as_completed(future_to_file):
                results.append(future.result())
                completed += 1
                if completed % 10 == 0 or completed == total:
                    print(f"   Progression: {completed}/{total} fichiers analysés", end='\r')
        
        print()  # Nouvelle ligne après la progression
        return results
    
    def query_llm(self, prompt: str, stream: bool = False) -> str:
        """
        Interroge le LLM local via l'API Ollama
        
        Args:
            prompt: Le prompt à envoyer au LLM
            stream: Si True, affiche la réponse en temps réel
            
        Returns:
            La réponse du LLM
        """
        try:
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": stream
            }
            
            response = requests.post(
                self.llm_url,
                json=payload,
                stream=stream,
                timeout=120
            )
            
            if stream:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        json_response = json.loads(line)
                        chunk = json_response.get('response', '')
                        print(chunk, end='', flush=True)
                        full_response += chunk
                print()  # Nouvelle ligne à la fin
                return full_response
            else:
                result = response.json()
                return result.get('response', '')
                
        except requests.exceptions.ConnectionError:
            return "ERREUR: Impossible de se connecter au LLM local. Assurez-vous qu'Ollama est lancé (ollama serve)."
        except Exception as e:
            return f"ERREUR LLM: {str(e)}"
    
    def select_suspicious_files(self, results: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        Sélectionne les fichiers les plus suspects en utilisant le LLM avec apprentissage
        """
        # Filtrer les erreurs
        valid_results = [r for r in results if 'error' not in r]
        
        # Trier par score de qualité (les plus mauvais en premier)
        sorted_results = sorted(valid_results, key=lambda x: x['quality_score'])
        
        # Préparer les données pour le LLM
        summary = f"Analyse de {len(valid_results)} fichiers audio.\n\n"
        
        # Ajouter les données d'apprentissage si disponibles
        learning_summary = self.learning_db.get_training_summary()
        if "Aucune" not in learning_summary:
            summary += "=== DONNÉES D'APPRENTISSAGE ===\n"
            summary += learning_summary + "\n\n"
            summary += "Utilise ces données pour affiner ta sélection.\n\n"
        
        summary += "Top 20 fichiers avec les scores de qualité les plus bas:\n\n"
        
        for i, r in enumerate(sorted_results[:20], 1):
            summary += f"{i}. {r['file']}\n"
            summary += f"   Score qualité: {r['quality_score']}/100\n"
            summary += f"   Clipping: {r['clipping_ratio']}%\n"
            summary += f"   SNR: {r['snr_db']} dB\n"
            summary += f"   Taux craquements: {r['crackling_rate']}\n\n"
        
        # Demander au LLM de sélectionner les plus problématiques
        prompt = f"""{summary}

Tu es un système d’aide à la décision spécialisé en contrôle qualité audio, utilisant des métriques objectives, un modèle ML classique et l’historique stocké en base.

Parmi ces {file_count} fichiers, sélectionne exactement les {top_n} fichiers présentant le plus **haut risque de défaut**.

Données fournies pour chaque fichier :  
- Clipping_ratio  
- SNR  
- Crackling_rate  
- Quality_score  
- Score de suspicion ML [0-1]  
- Historique de similarité avec fichiers défectueux connus  

⚠️ **Règles strictes :**  
1. La précision prime sur la quantité.  
2. En cas de doute, sélectionner le fichier.  
3. Prioriser les signaux objectifs et le score ML continu.  
4. Inclure l’information historique pour ajuster la sélection.  
5. Appliquer toutes les règles de manière **déterministe et hiérarchique**.

**Critères hiérarchisés** (pour trier les fichiers) :  
- Clipping_ratio > 1.0% → CRITIQUE  
- SNR < 15 dB → CRITIQUE  
- Crackling_rate > 5 → MAJEUR  
- Quality_score < 60 → MAJEUR  
- Similarité historique avec fichiers défectueux → MAJEUR  
- Score ML continu → utilisé pour prioriser les fichiers en cas d’égalité

**Triage pour égalité de suspicion :**  
1. Clipping_ratio décroissant  
2. SNR croissant  
3. Crackling_rate décroissant  
4. Quality_score croissant  
5. Score ML décroissant  
6. Numéro de fichier croissant si tout est égal

**Sortie :**  
- UNIQUEMENT les numéros de fichiers et la **métrique de suspicion (valeur et moment de l’erreur)**  
- Ordonnés du plus suspect au moins suspect  
- Séparés par des virgules  
- **Aucun autre texte**
"""
        
        print("\n=== Consultation du LLM pour sélection intelligente ===\n")
        llm_response = self.query_llm(prompt, stream=True)
        
        # Parser la réponse du LLM
        try:
            selected_indices = [int(x.strip()) - 1 for x in llm_response.split(',') if x.strip().isdigit()]
            selected_files = [sorted_results[i] for i in selected_indices if i < len(sorted_results)]
            return selected_files[:top_n]
        except:
            # Fallback: retourner les top_n par score si le parsing échoue
            print("\nNote: Utilisation du tri par score (réponse LLM non parsable)")
            return sorted_results[:top_n]
    
    def interactive_review(self, suspicious_files: List[Dict]):
        """
        Permet à l'utilisateur d'écouter et d'évaluer les fichiers suspects
        """
        print("\n" + "=" * 70)
        print("MODE RÉVISION INTERACTIVE")
        print("=" * 70)
        print("\nVous allez maintenant écouter et évaluer chaque fichier suspect.")
        print("Vos réponses permettront au LLM d'apprendre et d'améliorer ses prédictions.\n")
        
        for i, file_data in enumerate(suspicious_files, 1):
            print("\n" + "-" * 70)
            print(f"Fichier {i}/{len(suspicious_files)}: {file_data['file']}")
            print("-" * 70)
            print(f"Chemin: {file_data['path']}")
            print(f"Score qualité: {file_data['quality_score']}/100")
            print(f"Durée: {file_data['duration']}s")
            print(f"Clipping: {file_data['clipping_ratio']}%")
            print(f"SNR: {file_data['snr_db']} dB")
            print(f"Craquements: {file_data['crackling_rate']}")
            print()
            
            # Options d'écoute
            while True:
                choice = input("Action: [E]couter | [D]éfectueux | [B]on | [S]auter | [Q]uitter: ").strip().upper()
                
                if choice == 'E':
                    # Écouter le fichier
                    duration_input = input("Durée à écouter en sec (Enter = tout): ").strip()
                    duration = float(duration_input) if duration_input else None
                    self.audio_player.play(file_data['path'], duration)
                    
                elif choice == 'D':
                    # Marquer comme défectueux
                    comment = input("Commentaire optionnel (type de défaut): ").strip()
                    self.learning_db.add_sample(file_data, 'defective', comment)
                    print("✓ Enregistré comme DÉFECTUEUX")
                    break
                    
                elif choice == 'B':
                    # Marquer comme bon
                    comment = input("Commentaire optionnel: ").strip()
                    self.learning_db.add_sample(file_data, 'good', comment)
                    print("✓ Enregistré comme BONNE QUALITÉ")
                    break
                    
                elif choice == 'S':
                    # Sauter ce fichier
                    print("→ Fichier sauté")
                    break
                    
                elif choice == 'Q':
                    # Quitter la révision
                    print("\nArrêt de la révision interactive.")
                    return
                    
                else:
                    print("⚠️  Choix invalide. Utilisez E, D, B, S ou Q")
        
        print("\n" + "=" * 70)
        print("RÉVISION INTERACTIVE TERMINÉE")
        print("=" * 70)
        stats = self.learning_db.data['statistics']
        print(f"Total évalué: {stats['total_reviewed']} fichiers")
        print(f"  - Défectueux: {stats['defective']}")
        print(f"  - Bonne qualité: {stats['good']}")
    
    def generate_report(self, selected_files: List[Dict]) -> str:
        """
        Génère un rapport détaillé des fichiers sélectionnés
        """
        report = "=" * 70 + "\n"
        report += "RAPPORT D'ANALYSE - FICHIERS SUSPECTS\n"
        report += "=" * 70 + "\n\n"
        
        for i, file_data in enumerate(selected_files, 1):
            report += f"{i}. {file_data['file']}\n"
            report += f"   Chemin: {file_data['path']}\n"
            report += f"   Score qualité: {file_data['quality_score']}/100\n"
            report += f"   Durée: {file_data['duration']}s\n"
            report += f"   Taux de clipping: {file_data['clipping_ratio']}%\n"
            report += f"   SNR: {file_data['snr_db']} dB\n"
            report += f"   Taux craquements: {file_data['crackling_rate']}\n"
            report += f"   Zero-crossing rate: {file_data['zero_crossing_rate']}\n"
            report += "-" * 70 + "\n"
        
        return report


def find_audio_files(root_folder: str) -> List[str]:
    """
    Recherche récursive de tous les fichiers audio dans l'arborescence
    
    Args:
        root_folder: Dossier racine de la recherche
        
    Returns:
        Liste des chemins vers les fichiers audio trouvés
    """
    audio_extensions = ['.wav', '.mp3', '.flac', '.wma', '.aac', '.ogg', '.m4a']
    audio_files = []
    
    print(f"🔍 Recherche récursive dans '{root_folder}'...")
    
    for ext in audio_extensions:
        # Recherche récursive avec **/*
        files = list(Path(root_folder).rglob(f'*{ext}'))
        files.extend(list(Path(root_folder).rglob(f'*{ext.upper()}')))
        audio_files.extend(files)
    
    # Supprimer les doublons et convertir en strings
    audio_files = list(set([str(f) for f in audio_files]))
    
    return sorted(audio_files)


def ask_user_processing_mode(total_files: int) -> int:
    """
    Demande à l'utilisateur combien de fichiers traiter
    
    Returns:
        Nombre de fichiers à traiter
    """
    print(f"\n📊 {total_files} fichiers audio trouvés au total\n")
    print("Options de traitement:")
    print(f"  1. Analyser les 100 premiers fichiers (recommandé pour démarrer)")
    print(f"  2. Analyser TOUS les {total_files} fichiers")
    print("  3. Choisir un nombre personnalisé")
    print("  0. Quitter")
    
    while True:
        choice = input("\nVotre choix (0-3): ").strip()
        
        if choice == '0':
            print("Annulation...")
            exit(0)
        elif choice == '1':
            return min(100, total_files)
        elif choice == '2':
            confirm = input(f"⚠️  Confirmer l'analyse de {total_files} fichiers? (o/n): ").strip().lower()
            if confirm in ['o', 'oui', 'y', 'yes']:
                return total_files
            else:
                continue
        elif choice == '3':
            try:
                custom = int(input(f"Nombre de fichiers à analyser (1-{total_files}): ").strip())
                if 1 <= custom <= total_files:
                    return custom
                else:
                    print(f"⚠️  Veuillez entrer un nombre entre 1 et {total_files}")
            except ValueError:
                print("⚠️  Veuillez entrer un nombre valide")
        else:
            print("⚠️  Choix invalide, veuillez entrer 0, 1, 2 ou 3")


def main():
    """
    Fonction principale - Exemple d'utilisation
    """
    print("=" * 70)
    print("ANALYSEUR DE QUALITÉ AUDIO AVEC LLM LOCAL ET APPRENTISSAGE")
    print("=" * 70)
    
    # Demander le dossier à analyser
    print("\n📁 Configuration")
    default_folder = "./audio_samples"
    audio_folder = input(f"Dossier à analyser (défaut: {default_folder}): ").strip()
    if not audio_folder:
        audio_folder = default_folder
    
    if not os.path.exists(audio_folder):
        print(f"⚠️  Dossier '{audio_folder}' non trouvé.")
        create = input("Voulez-vous le créer? (o/n): ").strip().lower()
        if create in ['o', 'oui', 'y', 'yes']:
            os.makedirs(audio_folder)
            print(f"✓ Dossier '{audio_folder}' créé. Placez-y vos fichiers audio et relancez le script.")
        return
    
    # Initialiser l'analyseur
    analyzer = AudioQualityAnalyzer(
        llm_url="http://localhost:11434/api/generate",
        llm_model="llama2"  # Changez selon votre modèle installé
    )
    
    # Vérifier la connexion au LLM
    print("\nTest de connexion au LLM local...")
    test_response = analyzer.query_llm("Réponds simplement 'OK' si tu me reçois.")
    if "ERREUR" in test_response:
        print(f"\n⚠️  {test_response}")
        print("\nPour installer Ollama:")
        print("1. Téléchargez: https://ollama.ai/")
        print("2. Lancez: ollama serve")
        print("3. Installez un modèle: ollama pull llama2")
        return
    print("✓ LLM connecté avec succès\n")
    
    # Afficher les statistiques d'apprentissage existantes
    stats = analyzer.learning_db.data['statistics']
    if stats['total_reviewed'] > 0:
        print(f"📚 Base d'apprentissage: {stats['total_reviewed']} fichiers déjà évalués")
        print(f"   (Défectueux: {stats['defective']}, Bonne qualité: {stats['good']})\n")
    
    # Recherche récursive des fichiers audio
    all_audio_files = find_audio_files(audio_folder)
    
    if not all_audio_files:
        print(f"⚠️  Aucun fichier audio trouvé dans '{audio_folder}'")
        print("Extensions recherchées: .wav, .mp3, .flac, .wma, .aac, .ogg, .m4a")
        return
    
    # Demander si l'utilisateur veut détecter les doublons
    detect_duplicates = input("\nDétecter les doublons et fichiers vides? (o/n): ").strip().lower()
    duplicate_results = None
    
    if detect_duplicates in ['o', 'oui', 'y', 'yes']:
        duplicate_detector = DuplicateDetector()
        duplicate_results = duplicate_detector.analyze_files(all_audio_files)
        
        # Afficher le rapport de doublons
        print("\n" + duplicate_detector.generate_report(duplicate_results))
        
        # Sauvegarder le rapport de doublons
        duplicate_report_file = f"duplicate_report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(duplicate_report_file, 'w', encoding='utf-8') as f:
            # Convertir les tuples en strings pour JSON
            serializable_results = {
                'empty_files': duplicate_results['empty_files'],
                'duplicates_by_hash': {k: v for k, v in duplicate_results['duplicates_by_hash'].items()},
                'duplicates_by_name': {k: v for k, v in duplicate_results['duplicates_by_name'].items()},
                'duplicates_by_tags': {f"{k[0]} - {k[1]}": v for k, v in duplicate_results['duplicates_by_tags'].items()},
                'stats': duplicate_results['stats']
            }
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Rapport de doublons sauvegardé dans '{duplicate_report_file}'")
        
        # Classifier automatiquement les fichiers vides comme défectueux
        if duplicate_results['empty_files']:
            print(f"\n⚠️  {len(duplicate_results['empty_files'])} fichiers vides détectés.")
            print("   Ces fichiers seront automatiquement classés comme DÉFECTUEUX dans l'analyse.")
    
    # Demander à l'utilisateur combien de fichiers traiter
    num_to_process = ask_user_processing_mode(len(all_audio_files))
    
    # Sélectionner les fichiers à traiter
    audio_files = all_audio_files[:num_to_process]
    
    print(f"\n🔍 Analyse de {len(audio_files)} fichiers en cours...")
    print("⏳ Cela peut prendre quelques minutes...\n")
    
    # Analyser les fichiers
    results = analyzer.analyze_batch(audio_files, max_workers=4)
    
    # Séparer les fichiers vides et les fichiers avec erreurs
    empty_files_results = [r for r in results if r.get('auto_classified') == 'defective']
    error_files = [r for r in results if 'error' in r]
    valid_results = [r for r in results if 'error' not in r and r.get('auto_classified') != 'defective']
    
    print(f"✓ Analyse terminée: {len(results)} fichiers traités")
    if empty_files_results:
        print(f"   - {len(empty_files_results)} fichiers vides (auto-classés comme défectueux)")
    if error_files:
        print(f"   - {len(error_files)} fichiers avec erreurs")
    print(f"   - {len(valid_results)} fichiers valides analysés\n")
    
    # Demander combien de fichiers suspects afficher
    default_top_n = 10
    top_n_input = input(f"Nombre de fichiers suspects à identifier (défaut: {default_top_n}): ").strip()
    top_n = int(top_n_input) if top_n_input.isdigit() else default_top_n
    
    # Sélectionner les fichiers suspects avec l'aide du LLM (uniquement les fichiers valides)
    suspicious_files = []
    if valid_results:
        suspicious_files = analyzer.select_suspicious_files(valid_results, top_n=top_n)
    
    # Ajouter les fichiers vides aux suspects (en premier)
    all_suspicious = empty_files_results + suspicious_files
    
    # Générer et afficher le rapport
    if all_suspicious:
        print("\n" + analyzer.generate_report(all_suspicious[:top_n + len(empty_files_results)]))
    
    # Demander si l'utilisateur veut faire la révision interactive
    review = input("\nVoulez-vous écouter et évaluer ces fichiers? (o/n): ").strip().lower()
    if review in ['o', 'oui', 'y', 'yes']:
        # Ne proposer l'écoute que pour les fichiers non-vides
        reviewable_files = [f for f in all_suspicious if f.get('auto_classified') != 'defective']
        if reviewable_files:
            analyzer.interactive_review(reviewable_files)
        else:
            print("Aucun fichier à écouter (tous les fichiers suspects sont vides).")
    
    # Sauvegarder les résultats
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"audio_analysis_{timestamp}.json"
    
    output_data = {
        'analysis_date': timestamp,
        'root_folder': audio_folder,
        'total_files_found': len(all_audio_files),
        'files_analyzed': len(results),
        'empty_files': len(empty_files_results),
        'error_files': len(error_files),
        'valid_files': len(valid_results),
        'top_n_suspicious': top_n,
        'suspicious_files': all_suspicious,
        'all_results': results,
        'learning_statistics': analyzer.learning_db.data['statistics']
    }
    
    # Ajouter les résultats de doublons si disponibles
    if duplicate_results:
        output_data['duplicate_detection'] = {
            'performed': True,
            'stats': duplicate_results['stats']
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés dans '{output_file}'")
    print(f"💾 Base d'apprentissage sauvegardée dans '{analyzer.learning_db.db_file}'")
    print(f"\n✅ Processus terminé! Le LLM s'améliorera à chaque session d'évaluation.")


if __name__ == "__main__":
    main()
