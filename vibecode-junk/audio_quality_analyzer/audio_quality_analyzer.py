"""
Analyseur de qualité audio avec interaction LLM local
Détecte les craquements, clipping, bruit de fond dans des fichiers audio

Installation des dépendances:
pip install librosa soundfile numpy scipy requests

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
from typing import List, Dict, Tuple
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.analyze_audio_file, fp): fp 
                for fp in file_paths
            }
            
            for future in as_completed(future_to_file):
                results.append(future.result())
        
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
        Sélectionne les fichiers les plus suspects en utilisant le LLM
        """
        # Filtrer les erreurs
        valid_results = [r for r in results if 'error' not in r]
        
        # Trier par score de qualité (les plus mauvais en premier)
        sorted_results = sorted(valid_results, key=lambda x: x['quality_score'])
        
        # Préparer les données pour le LLM
        summary = f"Analyse de {len(valid_results)} fichiers audio.\n\n"
        summary += "Top 20 fichiers avec les scores de qualité les plus bas:\n\n"
        
        for i, r in enumerate(sorted_results[:20], 1):
            summary += f"{i}. {r['file']}\n"
            summary += f"   Score qualité: {r['quality_score']}/100\n"
            summary += f"   Clipping: {r['clipping_ratio']}%\n"
            summary += f"   SNR: {r['snr_db']} dB\n"
            summary += f"   Taux craquements: {r['crackling_rate']}\n\n"
        
        # Demander au LLM de sélectionner les 10 plus problématiques
        prompt = f"""{summary}

Tu es un expert en analyse audio. Parmi ces 20 fichiers, sélectionne les {top_n} fichiers qui nécessitent le plus une vérification manuelle.

Base ta sélection sur:
1. Score de qualité global très bas
2. Taux de clipping élevé (>1% est critique)
3. SNR faible (<15 dB est problématique)
4. Taux de craquements élevé (>5 est suspect)

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


def main():
    """
    Fonction principale - Exemple d'utilisation
    """
    # Configuration
    AUDIO_FOLDER = "./audio_samples"  # Dossier contenant vos fichiers audio
    SAMPLE_SIZE = 100  # Nombre de fichiers à analyser
    TOP_N = 10  # Nombre de fichiers suspects à sélectionner
    
    print("=" * 70)
    print("ANALYSEUR DE QUALITÉ AUDIO AVEC LLM LOCAL")
    print("=" * 70)
    
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
    
    # Trouver les fichiers audio
    audio_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    audio_files = []
    
    if os.path.exists(AUDIO_FOLDER):
        for ext in audio_extensions:
            audio_files.extend(Path(AUDIO_FOLDER).glob(f'*{ext}'))
    else:
        print(f"⚠️  Dossier '{AUDIO_FOLDER}' non trouvé.")
        print("Créez ce dossier et placez-y vos fichiers audio.")
        return
    
    audio_files = [str(f) for f in audio_files[:SAMPLE_SIZE]]
    
    if not audio_files:
        print(f"⚠️  Aucun fichier audio trouvé dans '{AUDIO_FOLDER}'")
        return
    
    print(f"📁 {len(audio_files)} fichiers trouvés")
    print(f"🔍 Analyse en cours...\n")
    
    # Analyser les fichiers
    results = analyzer.analyze_batch(audio_files, max_workers=4)
    
    print(f"✓ Analyse terminée: {len(results)} fichiers traités\n")
    
    # Sélectionner les fichiers suspects avec l'aide du LLM
    suspicious_files = analyzer.select_suspicious_files(results, top_n=TOP_N)
    
    # Générer et afficher le rapport
    print("\n" + analyzer.generate_report(suspicious_files))
    
    # Sauvegarder les résultats
    output_file = "audio_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_analyzed': len(results),
            'suspicious_files': suspicious_files,
            'all_results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés dans '{output_file}'")
    print(f"\n✅ Processus terminé! Vérifiez manuellement les {TOP_N} fichiers identifiés.")


if __name__ == "__main__":
    main()
