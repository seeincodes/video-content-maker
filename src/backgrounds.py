"""Background video handling — load gameplay clips or generate procedural backgrounds."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from moviepy import VideoClip, VideoFileClip, concatenate_videoclips

from .config import BACKGROUNDS_DIR, FPS, VIDEO_HEIGHT, VIDEO_WIDTH


def load_background(
    path: str | Path | None,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = FPS,
) -> VideoClip:
    """Load a background video, or generate a procedural one if no file is provided."""
    if path and Path(path).exists():
        return _load_video_file(Path(path), duration, width, height)

    # Check for any clips in the backgrounds directory
    bg_clip = _find_background_clip(duration, width, height)
    if bg_clip is not None:
        return bg_clip

    # Fallback: generate a procedural animated background
    return _generate_procedural_background(duration, width, height, fps)


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


def _generate_procedural_background(
    duration: float,
    width: int,
    height: int,
    fps: int,
) -> VideoClip:
    """Generate a dynamic gradient background with moving particles."""

    # Pre-compute particle positions (deterministic)
    rng = np.random.RandomState(42)
    n_particles = 30
    p_speed_x = rng.uniform(-50, 50, n_particles)
    p_speed_y = rng.uniform(-150, -50, n_particles)
    p_start_x = rng.uniform(0, width, n_particles)
    p_start_y = rng.uniform(0, height, n_particles)
    p_sizes = rng.randint(3, 8, n_particles)
    p_brightness = rng.randint(150, 255, n_particles)

    # Pre-compute y ratios for vectorized gradient
    y_ratios = np.linspace(0, 1, height).reshape(-1, 1)

    def make_frame(t: float) -> np.ndarray:
        phase = t * 0.3

        # Vectorized gradient computation
        r = (20 + 40 * (0.5 + 0.5 * np.sin(phase + y_ratios * 3))).astype(np.uint8)
        g = (10 + 20 * (0.5 + 0.5 * np.sin(phase * 1.3 + y_ratios * 2))).astype(np.uint8)
        b = (60 + 80 * (0.5 + 0.5 * np.sin(phase * 0.7 + y_ratios * 4))).astype(np.uint8)

        frame = np.broadcast_to(
            np.stack([r, g, b], axis=-1), (height, width, 3)
        ).copy()

        # Scrolling grid lines
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

        # Floating particles
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
