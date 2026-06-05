"""Caption rendering with multiple style presets for brainrot-style videos."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from moviepy import VideoClip
from PIL import Image, ImageDraw, ImageFont

from .config import (
    CAPTION_STYLES,
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


def _load_font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font at the given size, falling back to default."""
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def _draw_text_with_stroke(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    stroke_color: str,
    stroke_width: int,
) -> None:
    """Draw text with a stroke/outline."""
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    draw.text((x, y), text, font=font, fill=fill)


def _auto_scale_fonts(
    draw: ImageDraw.ImageDraw,
    word_texts: list[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    highlight_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    active_idx: int,
    max_width: float,
    font_path: str | None,
    font_size: int,
    highlight_font_size: int,
) -> tuple[
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
    list[float],
    float,
]:
    """Measure and auto-scale fonts if text overflows max_width."""
    space_width = draw.textlength(" ", font=font)
    word_widths = []
    total_width = 0.0
    for i, wt in enumerate(word_texts):
        use_font = highlight_font if i == active_idx else font
        w = draw.textlength(wt, font=use_font)
        word_widths.append(w)
        total_width += w
    total_width += space_width * (len(word_texts) - 1)

    if total_width > max_width:
        scale = max_width / total_width
        scaled_font_size = max(24, int(font_size * scale))
        scaled_highlight_size = max(28, int(highlight_font_size * scale))
        font = _load_font(font_path, scaled_font_size)
        highlight_font = _load_font(font_path, scaled_highlight_size)

        space_width = draw.textlength(" ", font=font)
        word_widths = []
        for i, wt in enumerate(word_texts):
            use_font = highlight_font if i == active_idx else font
            w = draw.textlength(wt, font=use_font)
            word_widths.append(w)

    return font, highlight_font, word_widths, space_width


def _get_active_word_idx(group: WordGroup, current_time: float) -> int:
    """Determine which word in the group is currently active."""
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
    return active_word_idx


# --- Style renderers ---


def _render_classic(
    width: int,
    height: int,
    group: WordGroup,
    current_time: float,
    style: dict,
    font_path: str | None,
) -> np.ndarray:
    """Classic style: all words visible, active word highlighted in gold with pop-up."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = style["font_size"]
    highlight_font_size = style["highlight_font_size"]
    color = style["color"]
    highlight_color = style["highlight_color"]
    stroke_color = style["stroke_color"]
    stroke_width = style["stroke_width"]
    y_position = style["y_position"]

    font = _load_font(font_path, font_size)
    highlight_font = _load_font(font_path, highlight_font_size)

    active_word_idx = _get_active_word_idx(group, current_time)
    y = int(height * y_position)
    word_texts = [w.word.upper() for w in group.words]
    max_text_width = width * 0.9

    font, highlight_font, word_widths, space_width = _auto_scale_fonts(
        draw, word_texts, font, highlight_font, active_word_idx,
        max_text_width, font_path, font_size, highlight_font_size,
    )

    total_width = sum(word_widths) + space_width * (len(word_texts) - 1)
    x = (width - total_width) / 2

    for i, wt in enumerate(word_texts):
        is_active = i == active_word_idx
        use_font = highlight_font if is_active else font
        use_color = highlight_color if is_active else color
        word_y = y if not is_active else y - 5

        _draw_text_with_stroke(draw, x, word_y, wt, use_font, use_color, stroke_color, stroke_width)
        x += word_widths[i] + space_width

    return np.array(img)


def _render_hormozi(
    width: int,
    height: int,
    group: WordGroup,
    current_time: float,
    style: dict,
    font_path: str | None,
) -> np.ndarray:
    """Hormozi style: one word at a time, very large, alternating colors."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = style["font_size"]
    stroke_color = style["stroke_color"]
    stroke_width = style["stroke_width"]
    y_position = style["y_position"]
    alternate_colors = style.get("alternate_colors", ["#FFFF00", "white", "#00FF88"])

    font = _load_font(font_path, font_size)

    active_word_idx = _get_active_word_idx(group, current_time)
    word = group.words[active_word_idx]
    word_text = word.word.upper()

    color = alternate_colors[active_word_idx % len(alternate_colors)]

    text_width = draw.textlength(word_text, font=font)
    max_text_width = width * 0.85
    if text_width > max_text_width:
        scale = max_text_width / text_width
        scaled_size = max(60, int(font_size * scale))
        font = _load_font(font_path, scaled_size)
        text_width = draw.textlength(word_text, font=font)

    x = (width - text_width) / 2
    y = int(height * y_position)

    _draw_text_with_stroke(draw, x, y, word_text, font, color, stroke_color, stroke_width)

    return np.array(img)


def _render_karaoke(
    width: int,
    height: int,
    group: WordGroup,
    current_time: float,
    style: dict,
    font_path: str | None,
) -> np.ndarray:
    """Karaoke style: all words visible, spoken words colored, unspoken words dimmed."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = style["font_size"]
    color = style["color"]
    highlight_color = style["highlight_color"]
    stroke_color = style["stroke_color"]
    stroke_width = style["stroke_width"]
    y_position = style["y_position"]

    font = _load_font(font_path, font_size)

    word_texts = [w.word.upper() for w in group.words]
    max_text_width = width * 0.9

    # Use uniform font for karaoke (no highlight size difference)
    space_width = draw.textlength(" ", font=font)
    word_widths = []
    total_width = 0.0
    for wt in word_texts:
        w = draw.textlength(wt, font=font)
        word_widths.append(w)
        total_width += w
    total_width += space_width * (len(word_texts) - 1)

    if total_width > max_text_width:
        scale = max_text_width / total_width
        scaled_size = max(24, int(font_size * scale))
        font = _load_font(font_path, scaled_size)
        space_width = draw.textlength(" ", font=font)
        word_widths = []
        total_width = 0.0
        for wt in word_texts:
            w = draw.textlength(wt, font=font)
            word_widths.append(w)
            total_width += w
        total_width += space_width * (len(word_texts) - 1)

    x = (width - total_width) / 2
    y = int(height * y_position)

    for i, wt in enumerate(word_texts):
        word_timing = group.words[i]
        # Words that have already been spoken or are currently active get highlighted
        if current_time >= word_timing.start_s:
            use_color = highlight_color
        else:
            use_color = color

        _draw_text_with_stroke(draw, x, y, wt, font, use_color, stroke_color, stroke_width)
        x += word_widths[i] + space_width

    return np.array(img)


def _render_mr_beast(
    width: int,
    height: int,
    group: WordGroup,
    current_time: float,
    style: dict,
    font_path: str | None,
) -> np.ndarray:
    """MrBeast style: bold text with colored background boxes behind active word."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = style["font_size"]
    highlight_font_size = style["highlight_font_size"]
    color = style["color"]
    stroke_color = style["stroke_color"]
    stroke_width = style["stroke_width"]
    y_position = style["y_position"]
    box_color = style.get("box_color", "#FF0050")
    box_padding = style.get("box_padding", 12)

    font = _load_font(font_path, font_size)
    highlight_font = _load_font(font_path, highlight_font_size)

    active_word_idx = _get_active_word_idx(group, current_time)
    y = int(height * y_position)
    word_texts = [w.word.upper() for w in group.words]
    max_text_width = width * 0.9

    font, highlight_font, word_widths, space_width = _auto_scale_fonts(
        draw, word_texts, font, highlight_font, active_word_idx,
        max_text_width, font_path, font_size, highlight_font_size,
    )

    total_width = sum(word_widths) + space_width * (len(word_texts) - 1)
    x = (width - total_width) / 2

    for i, wt in enumerate(word_texts):
        is_active = i == active_word_idx
        use_font = highlight_font if is_active else font

        if is_active:
            # Draw colored box behind active word
            active_bbox = use_font.getbbox(wt)
            active_height = active_bbox[3] - active_bbox[1] if active_bbox else highlight_font_size
            box_x1 = x - box_padding
            box_y1 = y - box_padding
            box_x2 = x + word_widths[i] + box_padding
            box_y2 = y + active_height + box_padding
            draw.rounded_rectangle(
                [box_x1, box_y1, box_x2, box_y2],
                radius=8,
                fill=box_color,
            )

        word_y = y
        _draw_text_with_stroke(draw, x, word_y, wt, use_font, color, stroke_color, stroke_width)
        x += word_widths[i] + space_width

    return np.array(img)


_STYLE_RENDERERS = {
    "group_highlight": _render_classic,
    "single_word": _render_hormozi,
    "progressive_fill": _render_karaoke,
    "boxed": _render_mr_beast,
}


def render_caption_frame(
    width: int,
    height: int,
    group: WordGroup,
    current_time: float,
    style_name: str = "classic",
    font_path: str | None = None,
) -> np.ndarray:
    """Render a single caption frame using the specified style preset."""
    style = CAPTION_STYLES.get(style_name, CAPTION_STYLES["classic"])
    mode = style["mode"]
    renderer = _STYLE_RENDERERS.get(mode, _render_classic)
    return renderer(width, height, group, current_time, style, font_path)


def _prerender_group_frames(
    width: int,
    height: int,
    group: WordGroup,
    style_name: str,
    font_path: str | None,
) -> list[tuple[float, float, np.ndarray]]:
    """Pre-render all distinct frames for a word group.

    Instead of rendering per video frame (30fps), renders once per word transition.
    Returns list of (relative_start, relative_end, rgba_frame) tuples.
    """
    frames: list[tuple[float, float, np.ndarray]] = []
    group_start = group.start_s

    for word in group.words:
        # Render at the midpoint of each word's duration
        word_mid = (word.start_s + word.end_s) / 2.0
        frame = render_caption_frame(
            width=width,
            height=height,
            group=group,
            current_time=word_mid,
            style_name=style_name,
            font_path=font_path,
        )
        rel_start = word.start_s - group_start
        rel_end = word.end_s - group_start
        frames.append((rel_start, rel_end, frame))

    return frames


def create_caption_clips(
    word_timings: list[WordTiming],
    config: VideoConfig,
) -> list[VideoClip]:
    """Create moviepy clips for animated captions.

    Uses frame caching: pre-renders one frame per word state instead of
    re-rendering every video frame. This reduces PIL render calls from
    (30fps × duration) to just (num_words) per group.
    """
    style_name = config.caption_style
    style = CAPTION_STYLES.get(style_name, CAPTION_STYLES["classic"])
    words_per_group = style.get("words_per_group", config.words_per_group)

    groups = group_words(word_timings, words_per_group)
    clips: list[VideoClip] = []
    font_path = find_system_font()

    for group in groups:
        duration = group.end_s - group.start_s
        if duration <= 0:
            continue

        # Pre-render all word states for this group
        cached_frames = _prerender_group_frames(
            config.width, config.height, group, style_name, font_path
        )

        def make_frame_func(frames: list[tuple[float, float, np.ndarray]]):
            def make_frame(t):
                # Find the cached frame for this time
                for rel_start, rel_end, frame in frames:
                    if rel_start <= t < rel_end:
                        return frame[:, :, :3]
                # Fallback to last frame
                if frames:
                    return frames[-1][2][:, :, :3]
                return np.zeros((1, 1, 3), dtype=np.uint8)

            return make_frame

        def make_mask_func(frames: list[tuple[float, float, np.ndarray]]):
            def make_mask(t):
                for rel_start, rel_end, frame in frames:
                    if rel_start <= t < rel_end:
                        return frame[:, :, 3] / 255.0
                if frames:
                    return frames[-1][2][:, :, 3] / 255.0
                return np.zeros((1, 1), dtype=np.float64)

            return make_mask

        clip = VideoClip(make_frame_func(cached_frames), duration=duration)
        mask = VideoClip(
            make_mask_func(cached_frames),
            is_mask=True,
            duration=duration,
        )
        clip = clip.with_mask(mask).with_start(group.start_s).with_position((0, 0))
        clips.append(clip)

    return clips
