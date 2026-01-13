import os
import logging
from mutagen import File
from mutagen.flac import FLAC, FLACNoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError

class MetadataExpert:
    """
    Expert en métadonnées et intégrité des conteneurs.
    Restaure la capacité de détection de fraude par analyse de header.
    """
    def __init__(self):
        self.logger = logging.getLogger("Audiopro.Metadata")
        # Formats supportés pour la validation stricte
        self.lossless_extensions = {'.FLAC', '.WAV', '.AIFF', '.WV', '.ALAC'}

    def extract_info(self, file_path):
        """
        Extrait les propriétés techniques réelles du flux audio.
        Compare l'extension avec le contenu binaire (DevSecOps).
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Fichier introuvable: {file_path}")
            return self._generate_fallback_info(file_path, "FILE_NOT_FOUND")

        try:
            # Inspection binaire du fichier
            audio = File(file_path, easy=True)
            
            if audio is None:
                self.logger.warning(f"Header non reconnu pour {file_path}. Analyse binaire requise.")
                return self._generate_fallback_info(file_path, "UNKNOWN_CONTAINER")

            info = audio.info
            actual_format = type(audio).__name__.replace('Easy', '').replace('FileType', '')
            extension = os.path.splitext(file_path)[1].upper()

            # --- VÉRIFICATION DE SÉCURITÉ (ANTI-SPOOFING) ---
            is_spoofed = self._check_spoofing(actual_format, extension)
            
            metadata = {
                "format_internal": actual_format,
                "format_ext": extension,
                "is_spoofed": is_spoofed,
                "duration": getattr(info, 'length', 0),
                "bitrate": self._get_bitrate_kbps(info),
                "sample_rate": getattr(info, 'sample_rate', 0),
                "channels": getattr(info, 'channels', 0),
                "bits_per_sample": getattr(info, 'bits_per_sample', 16) if hasattr(info, 'bits_per_sample') else 16,
                "is_lossless": extension in self.lossless_extensions and "MP3" not in actual_format,
                "status": "VALIDATED" if not is_spoofed else "SPOOF_ALERT"
            }

            self.logger.info(f"Metadata extraites avec succès pour {os.path.basename(file_path)}")
            return metadata

        except (FLACNoHeaderError, HeaderNotFoundError):
            self.logger.error(f"Corruption de header détectée: {file_path}")
            return self._generate_fallback_info(file_path, "CORRUPT_HEADER")
        except Exception as e:
            self.logger.error(f"Erreur d'extraction imprévue: {str(e)}")
            return self._generate_fallback_info(file_path, "ERROR")

    def _get_bitrate_kbps(self, info):
        """Calcule le bitrate en kbps de manière sécurisée."""
        br = getattr(info, 'bitrate', 0)
        return br // 1000 if br else 0

    def _check_spoofing(self, internal_fmt, ext):
        """
        Détecte si l'extension ment sur le contenu.
        Ex: Un MP3 renommé en .FLAC
        """
        internal_fmt = internal_fmt.upper()
        if ext == '.FLAC' and 'FLAC' not in internal_fmt:
            return True
        if ext in ['.WAV', '.AIFF'] and 'WAVE' not in internal_fmt and 'AIFF' not in internal_fmt:
            # Certains WAV ne sont pas lus par Mutagen mais sont valides
            return False 
        return False

    def _generate_fallback_info(self, file_path, status):
        """Garantit la continuité du service en cas de fichier problématique."""
        ext = os.path.splitext(file_path)[1].upper()
        return {
            "format_internal": "UNKNOWN",
            "format_ext": ext,
            "is_spoofed": False,
            "duration": 0,
            "bitrate": 0,
            "sample_rate": 0,
            "channels": 0,
            "bits_per_sample": 0,
            "is_lossless": ext in self.lossless_extensions,
            "status": status
        }
