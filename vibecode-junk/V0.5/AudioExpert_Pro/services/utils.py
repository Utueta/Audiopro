import magic, re, unicodedata
from pathlib import Path

class SecurityUtils:
    @staticmethod
    def sanitize_path(file_path):
        path_str = unicodedata.normalize('NFC', file_path)
        path_str = re.sub(r'[;&|`$><*!\n\r]', '', path_str)
        return str(Path(path_str).resolve())

    @staticmethod
    def validate_mime(file_path, allowed):
        mime = magic.from_file(file_path, mime=True)
        return mime in allowed, mime

