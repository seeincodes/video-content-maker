"""Configuration and constants for the brainrot video generator."""

from dataclasses import dataclass, field
from pathlib import Path

# Video dimensions (vertical 9:16 for short-form content)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# Caption styling
CAPTION_FONT_SIZE = 80
CAPTION_HIGHLIGHT_FONT_SIZE = 90
CAPTION_COLOR = "white"
CAPTION_HIGHLIGHT_COLOR = "#FFD700"  # Gold highlight for current word
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 4
CAPTION_FONT = "Impact"
CAPTION_Y_POSITION = 0.45  # Fraction from top (center-ish of screen)
WORDS_PER_GROUP = 4  # Number of words to show at once

# TTS defaults
DEFAULT_VOICE = "en-US-ChristopherNeural"
DEFAULT_RATE = "+10%"  # Slightly faster for brainrot energy
DEFAULT_VOLUME = "+0%"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class VideoConfig:
    """Configuration for a single video generation run."""

    text: str
    voice: str = DEFAULT_VOICE
    rate: str = DEFAULT_RATE
    volume: str = DEFAULT_VOLUME
    background_video: str | None = None
    background_style: str = "purple_grid"
    output_path: str | None = None
    width: int = VIDEO_WIDTH
    height: int = VIDEO_HEIGHT
    fps: int = FPS
    caption_font_size: int = CAPTION_FONT_SIZE
    caption_color: str = CAPTION_COLOR
    caption_highlight_color: str = CAPTION_HIGHLIGHT_COLOR
    words_per_group: int = WORDS_PER_GROUP
    watermark: str = ""
    extra_voices: list[str] = field(default_factory=list)
