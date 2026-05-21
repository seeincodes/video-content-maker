"""Command-line interface for the brainrot video generator."""

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_RATE, DEFAULT_VOICE, VideoConfig
from .video import generate_video


def main():
    parser = argparse.ArgumentParser(
        description="Turn any text into an informative brainrot-style short-form video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from inline text
  brainrot "The mitochondria is the powerhouse of the cell"

  # Generate from a text file
  brainrot --file notes.txt

  # Customize voice and speed
  brainrot "Hello world" --voice en-US-AriaNeural --rate "+20%"

  # Use a specific background video
  brainrot "Hello world" --background gameplay.mp4
        """,
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="The text to convert into a brainrot video.",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Read text from a file instead of inline argument.",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: output/brainrot_output.mp4).",
    )
    parser.add_argument(
        "--voice", "-v",
        type=str,
        default=DEFAULT_VOICE,
        help=f"Edge-TTS voice name (default: {DEFAULT_VOICE}).",
    )
    parser.add_argument(
        "--rate", "-r",
        type=str,
        default=DEFAULT_RATE,
        help="Speech rate adjustment (default: %(default)s).",
    )
    parser.add_argument(
        "--background", "-b",
        type=str,
        default=None,
        help="Path to a background video file (gameplay, etc).",
    )
    parser.add_argument(
        "--words-per-group", "-w",
        type=int,
        default=4,
        help="Number of words to show at once in captions (default: 4).",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available English TTS voices and exit.",
    )

    args = parser.parse_args()

    if args.list_voices:
        _list_voices()
        return

    # Get text from argument or file
    text = args.text
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        text = file_path.read_text(encoding="utf-8").strip()

    if not text:
        print("Error: No text provided. Use positional arg or --file.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    config = VideoConfig(
        text=text,
        voice=args.voice,
        rate=args.rate,
        background_video=args.background,
        output_path=args.output,
        words_per_group=args.words_per_group,
    )

    print("🎬 Generating brainrot video...")
    print(f"   Voice: {config.voice}")
    print(f"   Rate: {config.rate}")
    print(f"   Words per group: {config.words_per_group}")
    print(f"   Text: {text[:80]}{'...' if len(text) > 80 else ''}")
    print()

    output_path = generate_video(config)
    print(f"\n✅ Video saved to: {output_path}")


def _list_voices():
    """Print available English TTS voices."""
    import asyncio

    from .tts import list_voices

    voices = asyncio.run(list_voices("en"))
    print(f"Available English voices ({len(voices)} total):\n")
    for v in sorted(voices, key=lambda x: x["ShortName"]):
        gender = v.get("Gender", "?")
        name = v["ShortName"]
        print(f"  {name:<35} ({gender})")


if __name__ == "__main__":
    main()
