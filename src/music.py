"""Background music generation and auto-ducking for brainrot videos."""

from __future__ import annotations

import logging
import tempfile

import numpy as np
from moviepy import AudioFileClip

from .tts import WordTiming

logger = logging.getLogger(__name__)

# Music presets: name -> description
MUSIC_PRESETS: dict[str, str] = {
    "lofi_chill": "Lo-fi chill beats with soft chords and mellow drums",
    "trap_energy": "High-energy trap beat with 808s and hi-hats",
    "epic_cinematic": "Dramatic cinematic swells with deep bass",
    "none": "No background music",
}

DEFAULT_MUSIC_PRESET = "lofi_chill"

# Auto-duck settings
DUCK_VOLUME = 0.15  # Music volume when narration is active (15%)
FULL_VOLUME = 0.45  # Music volume during silence (45%)
FADE_DURATION = 0.08  # Seconds to ramp between duck/full


def _generate_tone(freq: float, duration: float, sr: int, amplitude: float = 0.3) -> np.ndarray:
    """Generate a sine wave tone."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _generate_chord(
    freqs: list[float], duration: float, sr: int, amplitude: float = 0.15
) -> np.ndarray:
    """Generate a chord from multiple frequencies."""
    chord = np.zeros(int(sr * duration), dtype=np.float32)
    for freq in freqs:
        chord += _generate_tone(freq, duration, sr, amplitude / len(freqs))
    return chord


def _apply_envelope(audio: np.ndarray, attack: float, release: float, sr: int) -> np.ndarray:
    """Apply attack/release envelope to audio."""
    attack_samples = int(attack * sr)
    release_samples = int(release * sr)
    envelope = np.ones(len(audio), dtype=np.float32)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if release_samples > 0:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    return audio * envelope


def _generate_kick(sr: int) -> np.ndarray:
    """Generate a simple kick drum sound."""
    duration = 0.15
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freq_sweep = 150 * np.exp(-30 * t) + 40
    kick = 0.5 * np.sin(2 * np.pi * freq_sweep * t / sr * np.cumsum(np.ones_like(t)))
    kick *= np.exp(-8 * t)
    return kick.astype(np.float32)


def _generate_hihat(sr: int, duration: float = 0.05) -> np.ndarray:
    """Generate a hi-hat sound (filtered noise)."""
    samples = int(sr * duration)
    noise = np.random.default_rng(42).uniform(-0.2, 0.2, samples).astype(np.float32)
    envelope = np.exp(-40 * np.linspace(0, duration, samples))
    return noise * envelope


def _generate_lofi_chill(duration: float, sr: int = 44100) -> np.ndarray:
    """Generate a lo-fi chill beat loop."""
    total_samples = int(sr * duration)
    output = np.zeros(total_samples, dtype=np.float32)

    # Chord progression: Cmaj7 -> Am7 -> Fmaj7 -> G7 (2 beats each at ~85 BPM)
    bpm = 85
    beat_duration = 60.0 / bpm
    chords = [
        [261.63, 329.63, 392.0, 493.88],   # Cmaj7
        [220.0, 261.63, 329.63, 392.0],     # Am7
        [174.61, 220.0, 261.63, 329.63],    # Fmaj7
        [196.0, 246.94, 293.66, 349.23],    # G7
    ]
    chord_duration = beat_duration * 2

    # Generate repeating chord progression
    pos = 0
    while pos < total_samples:
        for chord_freqs in chords:
            chord = _generate_chord(chord_freqs, chord_duration, sr, amplitude=0.12)
            chord = _apply_envelope(chord, attack=0.05, release=0.1, sr=sr)
            end = min(pos + len(chord), total_samples)
            output[pos:end] += chord[: end - pos]
            pos += len(chord)
            if pos >= total_samples:
                break

    # Add drum pattern
    kick = _generate_kick(sr)
    hihat = _generate_hihat(sr)
    beat_samples = int(beat_duration * sr)

    beat_pos = 0
    beat_count = 0
    while beat_pos < total_samples:
        # Kick on beats 1 and 3
        if beat_count % 4 in (0, 2):
            end = min(beat_pos + len(kick), total_samples)
            output[beat_pos:end] += kick[: end - beat_pos]
        # Hi-hat on every beat
        end = min(beat_pos + len(hihat), total_samples)
        output[beat_pos:end] += hihat[: end - beat_pos]
        # Extra hi-hat on off-beats
        offbeat_pos = beat_pos + beat_samples // 2
        if offbeat_pos < total_samples:
            end = min(offbeat_pos + len(hihat), total_samples)
            output[offbeat_pos:end] += hihat[: end - offbeat_pos] * 0.5

        beat_pos += beat_samples
        beat_count += 1

    # Soft low-pass effect (simple moving average)
    window_size = 5
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    output = np.convolve(output, kernel, mode="same")

    return output


def _generate_trap_energy(duration: float, sr: int = 44100) -> np.ndarray:
    """Generate a high-energy trap beat."""
    total_samples = int(sr * duration)
    output = np.zeros(total_samples, dtype=np.float32)

    bpm = 140
    beat_duration = 60.0 / bpm
    beat_samples = int(beat_duration * sr)

    # 808 bass pattern
    bass_freqs = [55.0, 55.0, 65.41, 55.0]  # Sub bass notes
    bass_duration = beat_duration * 2
    pos = 0
    note_idx = 0
    while pos < total_samples:
        freq = bass_freqs[note_idx % len(bass_freqs)]
        bass = _generate_tone(freq, bass_duration, sr, amplitude=0.25)
        bass = _apply_envelope(bass, attack=0.01, release=0.3, sr=sr)
        end = min(pos + len(bass), total_samples)
        output[pos:end] += bass[: end - pos]
        pos += int(bass_duration * sr)
        note_idx += 1

    # Fast hi-hats (16th notes)
    hihat = _generate_hihat(sr, duration=0.03)
    sixteenth = beat_samples // 4
    pos = 0
    count = 0
    while pos < total_samples:
        amplitude = 0.3 if count % 4 == 0 else 0.15
        end = min(pos + len(hihat), total_samples)
        output[pos:end] += hihat[: end - pos] * amplitude
        pos += sixteenth
        count += 1

    # Hard kick on beats 1 and 3
    kick = _generate_kick(sr)
    beat_pos = 0
    beat_count = 0
    while beat_pos < total_samples:
        if beat_count % 4 in (0, 2):
            end = min(beat_pos + len(kick), total_samples)
            output[beat_pos:end] += kick[: end - beat_pos] * 1.3
        beat_pos += beat_samples
        beat_count += 1

    return output


def _generate_epic_cinematic(duration: float, sr: int = 44100) -> np.ndarray:
    """Generate dramatic cinematic swells."""
    total_samples = int(sr * duration)
    output = np.zeros(total_samples, dtype=np.float32)

    # Deep bass drone
    t = np.linspace(0, duration, total_samples, endpoint=False)
    drone = 0.15 * np.sin(2 * np.pi * 55 * t)  # A1
    drone += 0.08 * np.sin(2 * np.pi * 82.41 * t)  # E2
    output += drone.astype(np.float32)

    # Slow swelling pad (fades in and out over 8-second cycles)
    cycle_duration = 8.0
    cycle_samples = int(cycle_duration * sr)
    pad_freqs = [130.81, 164.81, 196.0, 246.94]  # Cm chord
    pos = 0
    while pos < total_samples:
        cycle_len = min(cycle_samples, total_samples - pos)
        swell = np.linspace(0, np.pi, cycle_len)
        envelope = np.sin(swell) * 0.12
        for freq in pad_freqs:
            tone_t = np.linspace(0, cycle_duration, cycle_len, endpoint=False)
            output[pos : pos + cycle_len] += (
                envelope * np.sin(2 * np.pi * freq * tone_t)
            ).astype(np.float32)
        pos += cycle_len

    # Subtle timpani hits every 4 seconds
    hit_interval = int(4.0 * sr)
    kick = _generate_kick(sr)
    pos = 0
    while pos < total_samples:
        end = min(pos + len(kick), total_samples)
        output[pos:end] += kick[: end - pos] * 0.8
        pos += hit_interval

    return output


_MUSIC_GENERATORS = {
    "lofi_chill": _generate_lofi_chill,
    "trap_energy": _generate_trap_energy,
    "epic_cinematic": _generate_epic_cinematic,
}


def generate_music_track(
    preset: str,
    duration: float,
    sr: int = 44100,
) -> np.ndarray:
    """Generate a music track for the given preset and duration."""
    generator = _MUSIC_GENERATORS.get(preset)
    if generator is None:
        return np.zeros(int(sr * duration), dtype=np.float32)
    audio = generator(duration, sr)
    # Normalize to prevent clipping
    peak = np.max(np.abs(audio))
    if peak > 0.9:
        audio = audio * (0.9 / peak)
    return audio


def apply_auto_ducking(
    music: np.ndarray,
    word_timings: list[WordTiming],
    sr: int = 44100,
) -> np.ndarray:
    """Apply auto-ducking: lower music volume when narration is active."""
    total_samples = len(music)
    volume_curve = np.full(total_samples, FULL_VOLUME, dtype=np.float32)

    fade_samples = int(FADE_DURATION * sr)

    for word in word_timings:
        start_sample = int(word.start_s * sr)
        end_sample = int(word.end_s * sr)
        start_sample = max(0, min(start_sample, total_samples))
        end_sample = max(0, min(end_sample, total_samples))

        volume_curve[start_sample:end_sample] = DUCK_VOLUME

    # Smooth the volume curve with fades
    if fade_samples > 1:
        smoothed = np.copy(volume_curve)
        for i in range(1, total_samples):
            diff = volume_curve[i] - smoothed[i - 1]
            max_change = (FULL_VOLUME - DUCK_VOLUME) / fade_samples
            if abs(diff) > max_change:
                smoothed[i] = smoothed[i - 1] + np.sign(diff) * max_change
            else:
                smoothed[i] = volume_curve[i]
        volume_curve = smoothed

    return music * volume_curve


def create_music_audio_clip(
    preset: str,
    duration: float,
    word_timings: list[WordTiming],
) -> AudioFileClip | None:
    """Generate a background music clip with auto-ducking applied.

    Returns None if preset is 'none'.
    """
    if preset == "none":
        return None

    sr = 44100
    music = generate_music_track(preset, duration, sr=sr)
    music = apply_auto_ducking(music, word_timings, sr=sr)

    # Fade in/out
    fade_in_samples = int(0.5 * sr)
    fade_out_samples = int(1.0 * sr)
    if fade_in_samples < len(music):
        music[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)
    if fade_out_samples < len(music):
        music[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

    # Convert mono to stereo and write as wav
    stereo = np.column_stack([music, music])

    # Write to temp wav file
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    _write_wav(tmp_path, stereo, sr)
    return AudioFileClip(tmp_path)


def _write_wav(path: str, audio: np.ndarray, sr: int) -> None:
    """Write a numpy array to a WAV file (16-bit PCM)."""
    import wave

    # Convert float32 [-1, 1] to int16
    audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
    n_channels = audio_int16.shape[1] if audio_int16.ndim == 2 else 1

    with wave.open(path, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
