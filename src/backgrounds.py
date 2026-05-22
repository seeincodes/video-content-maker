"""Background video handling — load gameplay clips or generate procedural backgrounds."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from moviepy import VideoClip, VideoFileClip, concatenate_videoclips

from .config import BACKGROUNDS_DIR, FPS, VIDEO_HEIGHT, VIDEO_WIDTH

# Registry of available procedural background styles
BACKGROUND_STYLES: dict[str, str] = {
    "purple_grid": "Purple gradient with scrolling grid and particles",
    "matrix": "Green falling code / Matrix-style digital rain",
    "ocean": "Deep blue ocean waves with light rays",
    "neon_city": "Cyberpunk neon city skyline with pulsing lights",
    "space": "Starfield with drifting nebula colors",
    "fire": "Orange/red fire gradient with rising embers",
    "retro_arcade": "Classic arcade CRT scanline aesthetic",
}

DEFAULT_BACKGROUND_STYLE = "purple_grid"


def load_background(
    path: str | Path | None,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
    style: str = DEFAULT_BACKGROUND_STYLE,
) -> VideoClip:
    """Load a background video, or generate a procedural one if no file is provided."""
    if path and Path(path).exists():
        return _load_video_file(Path(path), duration, width, height)

    # Check for any clips in the backgrounds directory
    bg_clip = _find_background_clip(duration, width, height)
    if bg_clip is not None:
        return bg_clip

    # Fallback: generate a procedural animated background
    generator = _STYLE_GENERATORS.get(style, _generate_purple_grid)
    return generator(duration, width, height, fps)


def _load_video_file(
    path: Path, duration: float, width: int, height: int
) -> VideoClip:
    """Load and prepare a video file as background."""
    clip = VideoFileClip(str(path))

    # Resize to fill the frame (crop to 9:16 if needed)
    clip_ratio = clip.w / clip.h
    target_ratio = width / height

    if clip_ratio > target_ratio:
        # Video is wider — scale by height, crop width
        clip = clip.resized(height=height)
        x_center = clip.w / 2
        x1 = int(x_center - width / 2)
        clip = clip.cropped(x1=x1, x2=x1 + width)
    else:
        # Video is taller — scale by width, crop height
        clip = clip.resized(width=width)
        y_center = clip.h / 2
        y1 = int(y_center - height / 2)
        clip = clip.cropped(y1=y1, y2=y1 + height)

    # Loop or trim to match duration
    if clip.duration < duration:
        n_loops = int(duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * n_loops)

    clip = clip.subclipped(0, duration)
    return clip


def _find_background_clip(
    duration: float, width: int, height: int
) -> VideoClip | None:
    """Look for video files in the backgrounds directory."""
    if not BACKGROUNDS_DIR.exists():
        return None

    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    candidates = [
        f for f in BACKGROUNDS_DIR.iterdir() if f.suffix.lower() in video_extensions
    ]

    if not candidates:
        return None

    chosen = random.choice(candidates)
    return _load_video_file(chosen, duration, width, height)


# ---------------------------------------------------------------------------
# Procedural background generators
# ---------------------------------------------------------------------------


def _generate_purple_grid(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Purple gradient with scrolling grid and floating particles."""
    rng = np.random.RandomState(42)
    n_particles = 30
    p_speed_x = rng.uniform(-50, 50, n_particles)
    p_speed_y = rng.uniform(-150, -50, n_particles)
    p_start_x = rng.uniform(0, width, n_particles)
    p_start_y = rng.uniform(0, height, n_particles)
    p_sizes = rng.randint(3, 8, n_particles)
    p_brightness = rng.randint(150, 255, n_particles)

    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.3
        r = (20 + 40 * (0.5 + 0.5 * np.sin(phase + y_ratios * 3))).astype(np.uint8)
        g = (10 + 20 * (0.5 + 0.5 * np.sin(phase * 1.3 + y_ratios * 2))).astype(np.uint8)
        b = (60 + 80 * (0.5 + 0.5 * np.sin(phase * 0.7 + y_ratios * 4))).astype(np.uint8)

        frame = np.broadcast_to(
            np.stack([r, g, b], axis=-1), (height, width, 3)
        ).copy()

        grid_spacing = 80
        scroll_speed = 200
        offset = int(t * scroll_speed) % grid_spacing

        for y in range(offset, height, grid_spacing):
            y_start = max(0, y - 1)
            y_end = min(height, y + 1)
            brightness = frame[y_start:y_end, :].astype(np.int16) + 30
            frame[y_start:y_end, :] = np.clip(brightness, 0, 255).astype(np.uint8)

        for x in range(0, width, grid_spacing):
            x_start = max(0, x - 1)
            x_end = min(width, x + 1)
            brightness = frame[:, x_start:x_end].astype(np.int16) + 20
            frame[:, x_start:x_end] = np.clip(brightness, 0, 255).astype(np.uint8)

        for i in range(n_particles):
            px = int((p_start_x[i] + p_speed_x[i] * t) % width)
            py = int((p_start_y[i] + p_speed_y[i] * t) % height)
            size = p_sizes[i]
            bright = p_brightness[i]
            y1, y2 = max(0, py - size), min(height, py + size)
            x1, x2 = max(0, px - size), min(width, px + size)
            region = frame[y1:y2, x1:x2].astype(np.float32)
            color = np.array([bright, bright, bright * 0.8], dtype=np.float32)
            frame[y1:y2, x1:x2] = np.clip(
                region * 0.5 + color * 0.5, 0, 255
            ).astype(np.uint8)

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _generate_matrix(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Green falling code — Matrix-style digital rain."""
    rng = np.random.RandomState(7)
    n_columns = width // 18
    col_x = np.linspace(0, width - 12, n_columns).astype(int)
    col_speed = rng.uniform(200, 600, n_columns)
    col_offset = rng.uniform(0, height * 2, n_columns)
    col_length = rng.randint(8, 25, n_columns)

    char_h = 20

    def make_frame(t: float) -> np.ndarray:
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 1] = 5  # very faint green tint

        for i in range(n_columns):
            head_y = int((col_offset[i] + col_speed[i] * t) % (height + col_length[i] * char_h))
            length = col_length[i]

            for j in range(length):
                cy = head_y - j * char_h
                if cy < -char_h or cy >= height:
                    continue
                y1 = max(0, cy)
                y2 = min(height, cy + char_h - 2)
                if y2 <= y1:
                    continue
                x1 = col_x[i]
                x2 = min(width, x1 + 12)

                if j == 0:
                    brightness = 255
                    frame[y1:y2, x1:x2] = [brightness, 255, brightness]
                else:
                    fade = max(0.15, 1.0 - j / length)
                    g_val = int(200 * fade)
                    r_val = int(40 * fade)
                    frame[y1:y2, x1:x2] = [r_val, g_val, r_val // 2]

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _generate_ocean(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Deep blue ocean waves with light rays from above."""
    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)
    x_ratios = np.linspace(0, 1, width).reshape(1, -1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.4

        wave1 = np.sin(y_ratios * 6 + phase + x_ratios * 3) * 0.5
        wave2 = np.sin(y_ratios * 4 - phase * 0.7 + x_ratios * 5) * 0.3
        combined = 0.5 + wave1 + wave2

        r = np.clip(5 + 15 * combined, 0, 255).astype(np.uint8)
        g = np.clip(20 + 60 * combined + 30 * (1 - y_ratios), 0, 255).astype(np.uint8)
        b = np.clip(80 + 120 * combined + 40 * (1 - y_ratios), 0, 255).astype(np.uint8)

        frame = np.stack(
            [np.broadcast_to(r, (height, width)),
             np.broadcast_to(g, (height, width)),
             np.broadcast_to(b, (height, width))],
            axis=-1,
        ).copy()

        # Light rays from top
        n_rays = 5
        for ray_i in range(n_rays):
            base = width * (ray_i + 0.5) / n_rays
            ray_x = int((base + np.sin(phase * 0.3 + ray_i) * 100) % width)
            ray_w = 40 + int(20 * np.sin(phase * 0.5 + ray_i * 2))
            for y in range(0, int(height * 0.7), 4):
                fade = max(0, 1.0 - y / (height * 0.7))
                spread = int(ray_w * (1 + y / height * 2))
                sx1 = max(0, ray_x - spread)
                sx2 = min(width, ray_x + spread)
                add = int(30 * fade * (0.5 + 0.5 * np.sin(phase + y * 0.01)))
                if add > 0:
                    region = frame[y:y + 3, sx1:sx2].astype(np.int16)
                    region += add
                    frame[y:y + 3, sx1:sx2] = np.clip(region, 0, 255).astype(np.uint8)

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _generate_neon_city(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Cyberpunk neon city skyline with pulsing colored lights."""
    rng = np.random.RandomState(99)
    n_buildings = 25
    b_x = sorted(rng.randint(0, width, n_buildings))
    b_widths = rng.randint(30, 90, n_buildings)
    b_heights = rng.randint(int(height * 0.2), int(height * 0.65), n_buildings)
    _color_options = np.array([
        [255, 0, 100], [0, 200, 255], [255, 0, 255],
        [0, 255, 150], [255, 100, 0],
    ])
    b_colors = _color_options[rng.randint(0, len(_color_options), n_buildings)]
    n_windows_per = rng.randint(3, 8, n_buildings)

    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.5

        # Dark sky gradient
        r = (10 + 20 * (1 - y_ratios)).astype(np.uint8)
        g = (5 + 10 * (1 - y_ratios)).astype(np.uint8)
        b = (30 + 40 * (1 - y_ratios)).astype(np.uint8)

        frame = np.broadcast_to(
            np.stack([r, g, b], axis=-1), (height, width, 3)
        ).copy()

        # Buildings
        for i in range(n_buildings):
            bx = b_x[i]
            bw = b_widths[i]
            bh = b_heights[i]
            x1 = max(0, bx)
            x2 = min(width, bx + bw)
            y1 = height - bh
            y2 = height

            frame[y1:y2, x1:x2] = [15, 15, 25]

            # Neon outline on top
            color = b_colors[i]
            pulse = 0.5 + 0.5 * np.sin(phase * 2 + i * 0.7)
            neon = (np.array(color) * pulse).astype(np.uint8)
            top_h = min(3, y2 - y1)
            frame[y1:y1 + top_h, x1:x2] = neon

            # Windows
            win_spacing = max(1, bw // max(1, n_windows_per[i]))
            for wi in range(n_windows_per[i]):
                wx = x1 + 5 + wi * win_spacing
                if wx + 6 >= x2:
                    break
                for wy_off in range(10, bh - 10, 25):
                    wy = y1 + wy_off
                    if wy + 8 >= y2:
                        break
                    lit = np.sin(phase + i + wi + wy_off * 0.1) > -0.3
                    if lit:
                        win_color = (np.array(color) * 0.3 * pulse).astype(np.uint8)
                        frame[wy:wy + 8, wx:wx + 6] = win_color

        # Neon glow reflection on ground
        ground_y = height - 30
        glow = int(40 * (0.5 + 0.5 * np.sin(phase)))
        ground_r = frame[ground_y:, :, 0].astype(np.int16)
        frame[ground_y:, :, 0] = np.clip(
            ground_r + glow // 2, 0, 255
        ).astype(np.uint8)
        ground_b = frame[ground_y:, :, 2].astype(np.int16)
        frame[ground_y:, :, 2] = np.clip(
            ground_b + glow, 0, 255
        ).astype(np.uint8)

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _generate_space(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Starfield with drifting nebula colors."""
    rng = np.random.RandomState(21)
    n_stars = 200
    s_x = rng.uniform(0, width, n_stars)
    s_y = rng.uniform(0, height, n_stars)
    s_brightness = rng.uniform(100, 255, n_stars)
    s_size = rng.choice([1, 1, 1, 2, 2, 3], n_stars)
    s_twinkle_speed = rng.uniform(1, 5, n_stars)

    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)
    x_ratios = np.linspace(0, 1, width).reshape(1, -1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.2

        # Nebula colors
        nebula_r = 10 + 30 * (0.5 + 0.5 * np.sin(phase + y_ratios * 2 + x_ratios * 1.5))
        nebula_g = 5 + 15 * (0.5 + 0.5 * np.sin(phase * 0.8 + y_ratios * 3))
        nebula_b = 20 + 50 * (0.5 + 0.5 * np.sin(phase * 0.6 + y_ratios * 1.5 + x_ratios * 2))

        r = np.clip(nebula_r, 0, 255).astype(np.uint8)
        g = np.clip(nebula_g, 0, 255).astype(np.uint8)
        b = np.clip(nebula_b, 0, 255).astype(np.uint8)

        frame = np.stack(
            [np.broadcast_to(r, (height, width)),
             np.broadcast_to(g, (height, width)),
             np.broadcast_to(b, (height, width))],
            axis=-1,
        ).copy()

        # Stars with twinkling
        for i in range(n_stars):
            sx = int(s_x[i])
            sy = int(s_y[i])
            twinkle = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(t * s_twinkle_speed[i] + i))
            bright = int(s_brightness[i] * twinkle)
            size = s_size[i]
            y1, y2 = max(0, sy - size), min(height, sy + size)
            x1, x2 = max(0, sx - size), min(width, sx + size)
            frame[y1:y2, x1:x2] = [bright, bright, min(255, int(bright * 1.1))]

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _generate_fire(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Orange/red fire gradient with rising embers."""
    rng = np.random.RandomState(13)
    n_embers = 40
    e_x = rng.uniform(0, width, n_embers)
    e_speed_y = rng.uniform(-200, -80, n_embers)
    e_speed_x = rng.uniform(-30, 30, n_embers)
    e_start_y = rng.uniform(height * 0.5, height * 1.5, n_embers)
    e_sizes = rng.randint(2, 6, n_embers)
    e_brightness = rng.uniform(200, 255, n_embers)

    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.6

        wave = 0.5 + 0.5 * np.sin(phase + y_ratios * 4)
        r = np.clip(40 + 180 * (1 - y_ratios) * wave, 0, 255).astype(np.uint8)
        g = np.clip(10 + 80 * (1 - y_ratios) * wave * 0.7, 0, 255).astype(np.uint8)
        b = np.clip(5 + 20 * (1 - y_ratios ** 2), 0, 255).astype(np.uint8)

        frame = np.broadcast_to(
            np.stack([r, g, b], axis=-1), (height, width, 3)
        ).copy()

        # Rising embers
        for i in range(n_embers):
            ex = int((e_x[i] + e_speed_x[i] * t) % width)
            ey = int((e_start_y[i] + e_speed_y[i] * t) % height)
            size = e_sizes[i]
            bright = e_brightness[i]
            flicker = 0.5 + 0.5 * np.sin(t * 8 + i * 3)
            y1, y2 = max(0, ey - size), min(height, ey + size)
            x1, x2 = max(0, ex - size), min(width, ex + size)
            if y2 > y1 and x2 > x1:
                ember_color = np.array(
                    [bright * flicker, bright * flicker * 0.5, 10],
                    dtype=np.float32,
                )
                region = frame[y1:y2, x1:x2].astype(np.float32)
                frame[y1:y2, x1:x2] = np.clip(
                    region * 0.4 + ember_color * 0.6, 0, 255
                ).astype(np.uint8)

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def _generate_retro_arcade(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Retro arcade CRT aesthetic with scanlines and color cycling."""
    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.8

        # Color cycling background
        r = (20 + 30 * (0.5 + 0.5 * np.sin(phase * 0.5 + y_ratios * 2))).astype(np.uint8)
        g = (10 + 25 * (0.5 + 0.5 * np.sin(phase * 0.7 + y_ratios * 3 + 2))).astype(np.uint8)
        b = (30 + 40 * (0.5 + 0.5 * np.sin(phase * 0.3 + y_ratios * 2.5 + 4))).astype(np.uint8)

        frame = np.broadcast_to(
            np.stack([r, g, b], axis=-1), (height, width, 3)
        ).copy()

        # CRT scanlines
        for y in range(0, height, 4):
            frame[y, :] = np.clip(
                frame[y, :].astype(np.int16) - 20, 0, 255
            ).astype(np.uint8)

        # Horizontal scroll bars (CRT interference)
        bar_y = int((t * 300) % (height + 200)) - 100
        bar_h = 60
        y1 = max(0, bar_y)
        y2 = min(height, bar_y + bar_h)
        if y2 > y1:
            frame[y1:y2, :] = np.clip(
                frame[y1:y2, :].astype(np.int16) + 25, 0, 255
            ).astype(np.uint8)

        # Pixel grid overlay
        grid_size = 6
        for gx in range(0, width, grid_size):
            if gx + 1 < width:
                frame[:, gx] = np.clip(
                    frame[:, gx].astype(np.int16) - 10, 0, 255
                ).astype(np.uint8)

        # Corner vignette
        center_y = height / 2
        center_x = width / 2
        max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
        ys = np.arange(height).reshape(-1, 1)
        xs = np.arange(width).reshape(1, -1)
        dist = np.sqrt((ys - center_y) ** 2 + (xs - center_x) ** 2)
        vignette = np.clip(1.0 - (dist / max_dist) ** 2 * 0.6, 0.4, 1.0)
        vignette_3d = np.broadcast_to(vignette[:, :, np.newaxis], (height, width, 3))
        frame = (frame.astype(np.float32) * vignette_3d).astype(np.uint8)

        return frame

    return VideoClip(make_frame, duration=duration).with_fps(fps)


# Map style names to generator functions
_STYLE_GENERATORS = {
    "purple_grid": _generate_purple_grid,
    "matrix": _generate_matrix,
    "ocean": _generate_ocean,
    "neon_city": _generate_neon_city,
    "space": _generate_space,
    "fire": _generate_fire,
    "retro_arcade": _generate_retro_arcade,
}
