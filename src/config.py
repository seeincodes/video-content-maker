"""Configuration and constants for the brainrot video generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

# Caption style presets
DEFAULT_CAPTION_STYLE = "classic"

CAPTION_STYLES: dict[str, dict[str, Any]] = {
    "classic": {
        "description": "Gold-highlighted active word, all words visible",
        "font_size": 80,
        "highlight_font_size": 90,
        "color": "white",
        "highlight_color": "#FFD700",
        "stroke_color": "black",
        "stroke_width": 4,
        "y_position": 0.45,
        "words_per_group": 4,
        "mode": "group_highlight",
    },
    "hormozi": {
        "description": "One word at a time, large, alternating yellow/white",
        "font_size": 130,
        "highlight_font_size": 130,
        "color": "white",
        "highlight_color": "#FFFF00",
        "stroke_color": "black",
        "stroke_width": 6,
        "y_position": 0.42,
        "words_per_group": 1,
        "mode": "single_word",
        "alternate_colors": ["#FFFF00", "white", "#00FF88"],
    },
    "karaoke": {
        "description": "Words fill with color as they are spoken",
        "font_size": 72,
        "highlight_font_size": 72,
        "color": "#666666",
        "highlight_color": "#00DDFF",
        "stroke_color": "black",
        "stroke_width": 3,
        "y_position": 0.45,
        "words_per_group": 5,
        "mode": "progressive_fill",
    },
    "mr_beast": {
        "description": "Bold text with colored background boxes",
        "font_size": 90,
        "highlight_font_size": 100,
        "color": "white",
        "highlight_color": "white",
        "stroke_color": "black",
        "stroke_width": 3,
        "y_position": 0.43,
        "words_per_group": 3,
        "mode": "boxed",
        "box_color": "#FF0050",
        "box_padding": 12,
    },
}

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
    use_stock_footage: bool = False
    output_path: str | None = None
    width: int = VIDEO_WIDTH
    height: int = VIDEO_HEIGHT
    fps: int = FPS
    caption_style: str = DEFAULT_CAPTION_STYLE
    caption_font_size: int = CAPTION_FONT_SIZE
    caption_color: str = CAPTION_COLOR
    caption_highlight_color: str = CAPTION_HIGHLIGHT_COLOR
    words_per_group: int = WORDS_PER_GROUP
    music_preset: str = "lofi_chill"
    watermark: str = ""
    extra_voices: list[str] = field(default_factory=list)
