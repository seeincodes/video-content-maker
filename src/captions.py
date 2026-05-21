"""Caption rendering with word-by-word highlighting for brainrot-style videos."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from moviepy import VideoClip
from PIL import Image, ImageDraw, ImageFont

from .config import (
    CAPTION_COLOR,
    CAPTION_FONT_SIZE,
    CAPTION_HIGHLIGHT_COLOR,
    CAPTION_HIGHLIGHT_FONT_SIZE,
    CAPTION_STROKE_COLOR,
    CAPTION_STROKE_WIDTH,
    CAPTION_Y_POSITION,
    WORDS_PER_GROUP,
    VideoConfig,
)
from .tts import WordTiming


@dataclass
class WordGroup:
    """A group of words displayed together on screen."""

    words: list[WordTiming]
    start_s: float
    end_s: float

    @property
    def text(self) -> str:
        return " ".join(w.word for w in self.words)


def group_words(
    word_timings: list[WordTiming], words_per_group: int = WORDS_PER_GROUP
) -> list[WordGroup]:
    """Group words into chunks that appear on screen together."""
    groups: list[WordGroup] = []
    for i in range(0, len(word_timings), words_per_group):
        chunk = word_timings[i : i + words_per_group]
        if not chunk:
            continue
        groups.append(
            WordGroup(
                words=chunk,
                start_s=chunk[0].start_s,
                end_s=chunk[-1].end_s,
            )
        )
    return groups


def find_system_font() -> str | None:
    """Try to find a bold system font for captions."""
    import subprocess

    font_names = [
        "Impact",
        "Arial-Bold",
        "DejaVu-Sans-Bold",
        "Liberation-Sans-Bold",
        "Noto-Sans-Bold",
        "FreeSans-Bold",
    ]
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{file}\n"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        available = result.stdout.strip().split("\n")
        for name in font_names:
            for font_path in available:
                if name.lower().replace("-", "") in font_path.lower().replace("-", ""):
                    return font_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def render_caption_frame(
    width: int,
    height: int,
    group: WordGroup,
    current_time: float,
    font_size: int = CAPTION_FONT_SIZE,
    highlight_font_size: int = CAPTION_HIGHLIGHT_FONT_SIZE,
    color: str = CAPTION_COLOR,
    highlight_color: str = CAPTION_HIGHLIGHT_COLOR,
    stroke_color: str = CAPTION_STROKE_COLOR,
    stroke_width: int = CAPTION_STROKE_WIDTH,
    y_position: float = CAPTION_Y_POSITION,
    font_path: str | None = None,
) -> np.ndarray:
    """Render a single caption frame with word highlighting as a transparent RGBA image."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if font_path is None:
        font_path = find_system_font()

    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        highlight_font = (
            ImageFont.truetype(font_path, highlight_font_size)
            if font_path
            else ImageFont.load_default()
        )
    except (OSError, IOError):
        font = ImageFont.load_default()
        highlight_font = ImageFont.load_default()

    active_word_idx = -1
    for i, word in enumerate(group.words):
        if word.start_s <= current_time <= word.end_s:
            active_word_idx = i
            break
    if active_word_idx == -1:
        for i, word in enumerate(group.words):
            if current_time < word.start_s:
                active_word_idx = max(0, i - 1)
                break
        else:
            active_word_idx = len(group.words) - 1

    y = int(height * y_position)
    word_texts = [w.word.upper() for w in group.words]

    # Measure total width
    space_width = draw.textlength(" ", font=font)
    total_width = 0
    word_widths = []
    for i, wt in enumerate(word_texts):
        use_font = highlight_font if i == active_word_idx else font
        w = draw.textlength(wt, font=use_font)
        word_widths.append(w)
        total_width += w
    total_width += space_width * (len(word_texts) - 1)

    x = (width - total_width) / 2

    for i, wt in enumerate(word_texts):
        is_active = i == active_word_idx
        use_font = highlight_font if is_active else font
        use_color = highlight_color if is_active else color
        word_y = y if not is_active else y - 5  # Slight pop-up for active word

        # Draw stroke/outline
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, word_y + dy), wt, font=use_font, fill=stroke_color)

        draw.text((x, word_y), wt, font=use_font, fill=use_color)
        x += word_widths[i] + space_width

    return np.array(img)


def create_caption_clips(
    word_timings: list[WordTiming],
    config: VideoConfig,
) -> list[VideoClip]:
    """Create moviepy clips for animated captions."""
    groups = group_words(word_timings, config.words_per_group)
    clips: list[VideoClip] = []
    font_path = find_system_font()

    for group in groups:
        duration = group.end_s - group.start_s
        if duration <= 0:
            continue

        def make_frame_func(grp: WordGroup, fp: str | None):
            def make_frame(t):
                current_time = grp.start_s + t
                frame = render_caption_frame(
                    width=config.width,
                    height=config.height,
                    group=grp,
                    current_time=current_time,
                    font_size=config.caption_font_size,
                    color=config.caption_color,
                    highlight_color=config.caption_highlight_color,
                    font_path=fp,
                )
                return frame[:, :, :3]  # RGB only for compositing

            return make_frame

        def make_mask_func(grp: WordGroup, fp: str | None):
            def make_mask(t):
                current_time = grp.start_s + t
                frame = render_caption_frame(
                    width=config.width,
                    height=config.height,
                    group=grp,
                    current_time=current_time,
                    font_size=config.caption_font_size,
                    color=config.caption_color,
                    highlight_color=config.caption_highlight_color,
                    font_path=fp,
                )
                return frame[:, :, 3] / 255.0  # Alpha channel as mask

            return make_mask

        clip = VideoClip(make_frame_func(group, font_path), duration=duration)
        mask = VideoClip(make_mask_func(group, font_path), ismask=True, duration=duration)
        clip = clip.with_mask(mask).with_start(group.start_s).with_position((0, 0))
        clips.append(clip)

    return clips
