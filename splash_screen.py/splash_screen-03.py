"""
ui/splash_screen.py - Application bootloader with progress display.

ARCHITECTURE.MD §1 - Initialization (The Bootloader):
"app.py initializes dependency injection and triggers splash_screen.py"

Purpose:
- Display application branding during startup
- Show initialization progress
- Provide status updates for each component
- Display errors if initialization fails
"""

from PySide6.QtWidgets import (
    QSplashScreen, QLabel, QVBoxLayout, QWidget, 
    QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont, QPainter, QColor
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class SplashScreen(QSplashScreen):
    """
    Splash screen displayed during application initialization.
    
    ARCHITECTURE.MD §1 - The Bootloader:
    Shows progress as components are initialized:
    1. Health checks (CUDA, Ollama, FFmpeg)
    2. DSP pipeline loading
    3. ML model loading
    4. LLM service connection
    5. Database initialization
    6. UI construction
    
    Features:
    - Application logo/branding
    - Progress bar (0-100%)
    - Status messages
    - Error display
    """
    
    def __init__(self):
        """
        Initialize splash screen.
        
        Creates splash with:
        - Logo/background image (if available)
        - Application title
        - Progress bar
        - Status label
        """
        # Create splash image
        logo_path = Path("assets/logo.png")
        
        if logo_path.exists():
            # Load custom logo
            pixmap = QPixmap(str(logo_path))
            # Scale if too large
            if pixmap.width() > 800 or pixmap.height() > 600:
                pixmap = pixmap.scaled(
                    800, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
        else:
            # Create default splash (dark background with branding)
            pixmap = self._create_default_splash()
        
        # Initialize splash screen
        super().__init__(
            pixmap,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        )
        
        # Progress tracking
        self._progress = 0
        self._total_steps = 7  # Number of initialization steps
        
        # Setup UI elements
        self._setup_ui()
        
        logger.info("Splash screen initialized")
    
    def _create_default_splash(self) -> QPixmap:
        """
        Create default splash screen with branding.
        
        Returns:
            QPixmap with application branding
        """
        width, height = 700, 450
        pixmap = QPixmap(width, height)
        
        # Dark background
        pixmap.fill(QColor(20, 20, 30))
        
        # Draw branding
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Title
        title_font = QFont("Arial", 42, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor(0, 255, 255))  # Cyan
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
            "AUDIOPRO"
        )
        
        # Subtitle
        subtitle_font = QFont("Arial", 16)
        painter.setFont(subtitle_font)
        painter.setPen(QColor(180, 180, 180))
        painter.drawText(
            0, height // 2 - 50,
            width, 50,
            Qt.AlignmentFlag.AlignCenter,
            "Industrial Audio Analysis & Library Cleaning"
        )
        
        # Version
        version_font = QFont("Arial", 12)
        painter.setFont(version_font)
        painter.setPen(QColor(120, 120, 120))
        painter.drawText(
            0, height - 40,
            width, 30,
            Qt.AlignmentFlag.AlignCenter,
            "Expert-Level Industrial Tool"
        )
        
        painter.end()
        
        return pixmap
    
    def _setup_ui(self):
        """
        Setup UI elements on splash screen.
        
        Elements:
        - Status label (bottom, centered)
        - Progress bar (below status)
        """
        # Status label styling
        self.setStyleSheet("""
            QSplashScreen {
                background-color: #14141E;
            }
        """)
        
        # Show initial message
        self
