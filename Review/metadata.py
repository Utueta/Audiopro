"""
Audiopro Metadata Engine v0.3.1
- Role: Forensic technical parameter extraction.
- Logic: Dual-Path (Mutagen + FFprobe fallback).
- Merged: Robust stream probing for tagless or corrupt files.
"""

import subprocess
import json
import logging
from pathlib import Path
from mutagen import File

logger = logging.getLogger("system.analyzer.metadata")

class MetadataExtractor:
    @staticmethod
    def get_info(file_path: str) -> dict:
        """
        Extracts technical specs and common tags.
        Primary: Mutagen (Fast). Fallback: FFprobe (Forensic).
        """
        info = {
            "bitrate": 0,
            "sample_rate": 0,
            "duration": 0.0,
            "channels": 0,
            "format": Path(file_path).suffix.upper().replace(".", ""),
            "tags": {}
        }

        # Path 1: Mutagen Tag Parsing
        try:
            audio = File(file_path)
            if audio is not None and audio.info:
                info["bitrate"] = getattr(audio.info, 'bitrate', 0) // 1000
                info["sample_rate"] = getattr(audio.info, 'sample_rate', 0)
                info["duration"] = getattr(audio.info, 'length', 0.0)
                info["channels"] = getattr(audio.info, 'channels', 0)
                if hasattr(audio, 'tags') and audio.tags:
                    info["tags"] = {k: str(v) for k, v in audio.tags.items()}
        except Exception as e:
            logger.warning(f"Mutagen failed for {file_path}: {e}")

        # Path 2: FFprobe Forensic Fallback (Triggered if technical data is missing)
        if info["bitrate"] == 0 or info["duration"] == 0:
            logger.info(f"Triggering FFprobe fallback for {Path(file_path).name}")
            info = MetadataExtractor._ffprobe_fallback(file_path, info)

        return info

    @staticmethod
    def _ffprobe_fallback(file_path: str, info: dict) -> dict:
        """Probes the actual stream headers using FFmpeg tools."""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", file_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            data = json.loads(result.stdout)
            
            if "format" in data:
                f = data["format"]
                info["bitrate"] = int(f.get("bit_rate", 0)) // 1000 if f.get("bit_rate") else info["bitrate"]
                info["duration"] = float(f.get("duration", 0.0)) if f.get("duration") else info["duration"]
            
            if "streams" in data and len(data["streams"]) > 0:
                s = data["streams"][0]
                info["sample_rate"] = int(s.get("sample_rate", 0)) if s.get("sample_rate") else info["sample_rate"]
                info["channels"] = int(s.get("channels", 0)) if s.get("channels") else info["channels"]
                
        except Exception as e:
            logger.error(f"FFprobe critical failure for {file_path}: {e}")
            
        return info
