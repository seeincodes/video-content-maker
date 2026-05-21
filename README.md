# 🧠 Brainrot Generator

Turn any text into informative brainrot-style short-form videos — complete with TTS narration, word-by-word animated captions, and gameplay backgrounds.

## Features

- **Free TTS** via [edge-tts](https://github.com/rany2/edge-tts) (Microsoft Edge voices, no API key needed)
- **Animated captions** with word-by-word highlighting (gold highlight on active word)
- **Gameplay backgrounds** — drop your own clips in `assets/backgrounds/` or use the built-in procedural background
- **Vertical 9:16 format** optimized for TikTok, Reels, and YouTube Shorts
- **CLI & Web UI** — use from the command line or the Streamlit web app

## Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg (`sudo apt install ffmpeg` on Ubuntu)

### Install

```bash
# Clone the repo
git clone https://github.com/seeincodes/brainrot-generator.git
cd brainrot-generator

# Install dependencies
pip install -e ".[web,dev]"
```

### CLI Usage

```bash
# Generate from inline text
brainrot "The mitochondria is the powerhouse of the cell"

# Generate from a file
brainrot --file notes.txt

# Customize voice and speed
brainrot "Hello world" --voice en-US-AriaNeural --rate "+20%"

# Use your own background video
brainrot "Hello world" --background subway_surfer.mp4

# List available voices
brainrot --list-voices
```

### Web UI

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

## Adding Background Videos

Drop any gameplay clips (MP4, MOV, AVI, MKV, WebM) into `assets/backgrounds/`. The generator will randomly pick one and loop/crop it to fit. Popular choices:

- Subway Surfer gameplay
- Minecraft parkour
- Satisfying ASMR clips
- GTA driving footage

If no background clips are provided, a procedural animated background is generated automatically.

## Configuration

| Option | CLI Flag | Default | Description |
|--------|----------|---------|-------------|
| Voice | `--voice` | `en-US-ChristopherNeural` | Edge-TTS voice name |
| Rate | `--rate` | `+10%` | Speech speed adjustment |
| Background | `--background` | Auto-detect | Path to background video |
| Words/group | `--words-per-group` | `4` | Words shown at once in captions |
| Output | `--output` | `output/brainrot_output.mp4` | Output file path |

## Project Structure

```
brainrot-generator/
├── src/
│   ├── tts.py          # TTS generation with word-level timestamps
│   ├── captions.py     # Animated caption rendering
│   ├── backgrounds.py  # Background video loading/generation
│   ├── video.py        # Main compositing pipeline
│   ├── config.py       # Configuration and constants
│   └── cli.py          # Command-line interface
├── app.py              # Streamlit web UI
├── assets/
│   └── backgrounds/    # Drop gameplay clips here
├── output/             # Generated videos
└── pyproject.toml
```

## How It Works

1. **TTS Generation** — Text is converted to speech using edge-tts, which provides word-level timing data
2. **Caption Rendering** — Words are grouped and rendered frame-by-frame with the active word highlighted in gold
3. **Background** — A gameplay video (or procedural animation) is loaded and cropped to 9:16
4. **Compositing** — Audio, captions, and background are combined into a final MP4

## License

MIT
