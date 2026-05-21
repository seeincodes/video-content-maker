"""Text-to-speech generation using edge-tts with word-level timestamps."""

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

import edge_tts

from .config import DEFAULT_RATE, DEFAULT_VOICE, DEFAULT_VOLUME


@dataclass
class WordTiming:
    """Timing information for a single word."""

    word: str
    start_ms: float
    end_ms: float

    @property
    def start_s(self) -> float:
        return self.start_ms / 1000.0

    @property
    def end_s(self) -> float:
        return self.end_ms / 1000.0

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


@dataclass
class TTSResult:
    """Result of TTS generation."""

    audio_path: Path
    word_timings: list[WordTiming]
    duration_s: float


async def generate_tts(
    text: str,
    output_path: Path | None = None,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    volume: str = DEFAULT_VOLUME,
) -> TTSResult:
    """Generate TTS audio with word-level timestamps.

    Args:
        text: The text to convert to speech.
        output_path: Where to save the audio file. If None, uses a temp file.
        voice: The edge-tts voice to use.
        rate: Speech rate adjustment (e.g., "+10%").
        volume: Volume adjustment.

    Returns:
        TTSResult with audio path and word timings.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = Path(tmp.name)
        tmp.close()

    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)

    word_timings: list[WordTiming] = []
    max_end_ms: float = 0

    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                offset = chunk["offset"]  # in 100-nanosecond units
                duration = chunk["duration"]  # in 100-nanosecond units
                start_ms = offset / 10_000
                end_ms = (offset + duration) / 10_000
                word = chunk["text"]
                word_timings.append(WordTiming(word=word, start_ms=start_ms, end_ms=end_ms))
                max_end_ms = max(max_end_ms, end_ms)

    duration_s = max_end_ms / 1000.0 if max_end_ms > 0 else 0.0

    return TTSResult(
        audio_path=output_path,
        word_timings=word_timings,
        duration_s=duration_s,
    )


async def list_voices(language: str = "en") -> list[dict]:
    """List available edge-tts voices for a given language prefix."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith(language)]


def run_tts(
    text: str,
    output_path: Path | None = None,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    volume: str = DEFAULT_VOLUME,
) -> TTSResult:
    """Synchronous wrapper for generate_tts."""
    return asyncio.run(generate_tts(text, output_path, voice, rate, volume))
