"""
Analyseur de qualité audio avec interaction LLM local et apprentissage
Détecte les craquements, clipping, bruit de fond dans des fichiers audio
Permet l'écoute et l'apprentissage basé sur les retours utilisateur

Installation des dépendances:
pip install librosa soundfile numpy scipy requests pygame

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

# Pour la lecture audio
try:
    import pygame
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    AUDIO_PLAYBACK_AVAILABLE = False
    print("⚠️  pygame non installé. Lecture audio désactivée.")
    print("   Installez avec: pip install pygame")


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

Tu es un expert en analyse audio. Parmi ces 20 fichiers, sélectionne les {top_n} fichiers qui nécessitent le plus une vérification manuelle.

Base ta sélection sur:
1. Les données d'apprentissage précédentes (si disponibles)
2. Score de qualité global très bas
3. Taux de clipping élevé (>1% est critique)
4. SNR faible (<15 dB est problématique)
5. Taux de craquements élevé (>5 est suspect)

Réponds UNIQUEMENT avec les numéros des fichiers sélectionnés, séparés par des virgules (ex: 1,3,5,7,9,11,13,15,17,19).
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
    
    # Demander à l'utilisateur combien de fichiers traiter
    num_to_process = ask_user_processing_mode(len(all_audio_files))
    
    # Sélectionner les fichiers à traiter
    audio_files = all_audio_files[:num_to_process]
    
    print(f"\n🔍 Analyse de {len(audio_files)} fichiers en cours...")
    print("⏳ Cela peut prendre quelques minutes...\n")
    
    # Analyser les fichiers
    results = analyzer.analyze_batch(audio_files, max_workers=4)
    
    print(f"✓ Analyse terminée: {len(results)} fichiers traités\n")
    
    # Demander combien de fichiers suspects afficher
    default_top_n = 10
    top_n_input = input(f"Nombre de fichiers suspects à identifier (défaut: {default_top_n}): ").strip()
    top_n = int(top_n_input) if top_n_input.isdigit() else default_top_n
    
    # Sélectionner les fichiers suspects avec l'aide du LLM
    suspicious_files = analyzer.select_suspicious_files(results, top_n=top_n)
    
    # Générer et afficher le rapport
    print("\n" + analyzer.generate_report(suspicious_files))
    
    # Demander si l'utilisateur veut faire la révision interactive
    review = input("\nVoulez-vous écouter et évaluer ces fichiers? (o/n): ").strip().lower()
    if review in ['o', 'oui', 'y', 'yes']:
        analyzer.interactive_review(suspicious_files)
    
    # Sauvegarder les résultats
    timestamp = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"audio_analysis_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_date': timestamp,
            'root_folder': audio_folder,
            'total_files_found': len(all_audio_files),
            'files_analyzed': len(results),
            'top_n_suspicious': top_n,
            'suspicious_files': suspicious_files,
            'all_results': results,
            'learning_statistics': analyzer.learning_db.data['statistics']
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés dans '{output_file}'")
    print(f"💾 Base d'apprentissage sauvegardée dans '{analyzer.learning_db.db_file}'")
    print(f"\n✅ Processus terminé! Le LLM s'améliorera à chaque session d'évaluation.")


if __name__ == "__main__":
    main()