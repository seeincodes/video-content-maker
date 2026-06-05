"""Main video compositing pipeline — combines TTS audio, captions, and background."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from moviepy import AudioFileClip, CompositeVideoClip

from .backgrounds import load_background
from .captions import create_caption_clips
from .config import OUTPUT_DIR, VideoConfig
from .rewriter import rewrite_script
from .tts import run_tts

logger = logging.getLogger(__name__)


def generate_video(config: VideoConfig) -> Path:
    """Generate a complete brainrot-style video from text.

    Pipeline:
        1. Generate TTS audio with word-level timestamps
        2. Load or generate background video (stock footage or procedural)
        3. Render animated captions synced to audio
        4. Composite everything into final video
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 0: Rewrite script if requested
    narration_text = config.text
    if config.rewrite_mode != "none":
        logger.info("Rewriting script in '%s' mode...", config.rewrite_mode)
        narration_text = rewrite_script(config.text, config.rewrite_mode)
        logger.info("Rewritten text (%d words)", len(narration_text.split()))

    # Step 1: Generate TTS
    tts_result = run_tts(
        text=narration_text,
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

    background = None

    # Try stock footage if enabled
    if config.use_stock_footage:
        from .stock_footage import build_stock_footage_background, get_api_key

        api_key = get_api_key()
        if api_key:
            logger.info("Building stock footage background from Pexels...")
            background = build_stock_footage_background(
                text=config.text,
                word_timings=tts_result.word_timings,
                duration=total_duration,
                api_key=api_key,
                width=config.width,
                height=config.height,
                fps=config.fps,
                words_per_scene=config.scene_change_words,
                crossfade_duration=config.crossfade_duration,
            )
            if background is None:
                logger.warning(
                    "Stock footage fetch returned no results, falling back to procedural"
                )
        else:
            logger.warning(
                "PEXELS_API_KEY not set, falling back to procedural background"
            )

    if background is None:
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

    # Render (using 'fast' preset + max threads for speed)
    final.write_videofile(
        str(output_path),
        fps=config.fps,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=0,
        logger="bar",
    )

    # Cleanup temp files
    if tts_result.audio_path.parent == Path(tempfile.gettempdir()):
        tts_result.audio_path.unlink(missing_ok=True)

    return output_path
