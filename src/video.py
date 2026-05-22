"""Main video compositing pipeline — combines TTS audio, captions, and background."""

from __future__ import annotations

import tempfile
from pathlib import Path

from moviepy import AudioFileClip, CompositeVideoClip

from .backgrounds import load_background
from .captions import create_caption_clips
from .config import OUTPUT_DIR, VideoConfig
from .tts import run_tts


def generate_video(config: VideoConfig) -> Path:
    """Generate a complete brainrot-style video from text.

    Pipeline:
        1. Generate TTS audio with word-level timestamps
        2. Load or generate background video
        3. Render animated captions synced to audio
        4. Composite everything into final video
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate TTS
    tts_result = run_tts(
        text=config.text,
        voice=config.voice,
        rate=config.rate,
        volume=config.volume,
    )

    # Determine output path
    if config.output_path:
        output_path = Path(config.output_path)
    else:
        output_path = OUTPUT_DIR / "brainrot_output.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 2: Load background
    audio = AudioFileClip(str(tts_result.audio_path))
    total_duration = audio.duration + 0.5  # Small buffer at end

    background = load_background(
        path=config.background_video,
        duration=total_duration,
        width=config.width,
        height=config.height,
        fps=config.fps,
        style=config.background_style,
    )

    # Step 3: Create caption clips
    caption_clips = create_caption_clips(tts_result.word_timings, config)

    # Step 4: Composite
    all_clips = [background] + caption_clips
    final = CompositeVideoClip(all_clips, size=(config.width, config.height))
    final = final.with_duration(total_duration)
    final = final.with_audio(audio)

    # Render
    final.write_videofile(
        str(output_path),
        fps=config.fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar",
    )

    # Cleanup temp files
    if tts_result.audio_path.parent == Path(tempfile.gettempdir()):
        tts_result.audio_path.unlink(missing_ok=True)

    return output_path
