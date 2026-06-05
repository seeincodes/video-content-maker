"""Command-line interface for the brainrot video generator."""

import argparse
import sys
from pathlib import Path

from .backgrounds import BACKGROUND_STYLES, DEFAULT_BACKGROUND_STYLE
from .config import CAPTION_STYLES, DEFAULT_CAPTION_STYLE, DEFAULT_RATE, DEFAULT_VOICE, VideoConfig
from .rewriter import DEFAULT_REWRITE_MODE, REWRITE_MODES
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
  brainrot "Hello world" --voice en-US-AriaNeural --rate "+20%%"

  # Use a specific background style
  brainrot "Hello world" --background-style matrix

  # Use stock footage from Pexels (requires PEXELS_API_KEY env var)
  brainrot "Photosynthesis converts sunlight into energy" --stock-footage

  # Use a specific caption style
  brainrot "Hello world" --caption-style hormozi

  # Use a custom background video
  brainrot "Hello world" --background gameplay.mp4

  # List available background/caption styles
  brainrot --list-styles
  brainrot --list-caption-styles
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
        "--background-style", "-s",
        type=str,
        default=DEFAULT_BACKGROUND_STYLE,
        choices=list(BACKGROUND_STYLES.keys()),
        help="Procedural background style (default: %(default)s).",
    )
    parser.add_argument(
        "--stock-footage",
        action="store_true",
        default=False,
        help="Use Pexels stock footage matching the text content as background. "
        "Requires PEXELS_API_KEY environment variable.",
    )
    parser.add_argument(
        "--caption-style", "-c",
        type=str,
        default=DEFAULT_CAPTION_STYLE,
        choices=list(CAPTION_STYLES.keys()),
        help="Caption rendering style (default: %(default)s).",
    )
    parser.add_argument(
        "--rewrite",
        type=str,
        default=DEFAULT_REWRITE_MODE,
        choices=list(REWRITE_MODES.keys()),
        help="Rewrite text into a narration style before generating (default: %(default)s). "
        "Uses OpenAI API if OPENAI_API_KEY is set; otherwise local fallback.",
    )
    parser.add_argument(
        "--words-per-group", "-w",
        type=int,
        default=None,
        help="Number of words to show at once in captions (default: set by caption style).",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available English TTS voices and exit.",
    )
    parser.add_argument(
        "--list-styles",
        action="store_true",
        help="List available background styles and exit.",
    )
    parser.add_argument(
        "--list-caption-styles",
        action="store_true",
        help="List available caption style presets and exit.",
    )

    args = parser.parse_args()

    if args.list_voices:
        _list_voices()
        return

    if args.list_styles:
        _list_styles()
        return

    if args.list_caption_styles:
        _list_caption_styles()
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

    # Resolve words_per_group: explicit flag > style default
    words_per_group = args.words_per_group
    if words_per_group is None:
        words_per_group = CAPTION_STYLES[args.caption_style]["words_per_group"]

    config = VideoConfig(
        text=text,
        voice=args.voice,
        rate=args.rate,
        background_video=args.background,
        background_style=args.background_style,
        use_stock_footage=args.stock_footage,
        caption_style=args.caption_style,
        rewrite_mode=args.rewrite,
        output_path=args.output,
        words_per_group=words_per_group,
    )

    print("🎬 Generating brainrot video...")
    print(f"   Voice: {config.voice}")
    print(f"   Rate: {config.rate}")
    print(f"   Caption style: {config.caption_style}")
    if config.rewrite_mode != "none":
        print(f"   Rewrite: {config.rewrite_mode}")
    if config.use_stock_footage:
        print("   Background: Stock footage from Pexels")
    else:
        print(f"   Background: {config.background_style}")
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


def _list_styles():
    """Print available background styles."""
    print(f"Available background styles ({len(BACKGROUND_STYLES)} total):\n")
    for name, description in BACKGROUND_STYLES.items():
        default = " (default)" if name == DEFAULT_BACKGROUND_STYLE else ""
        print(f"  {name:<15} {description}{default}")


def _list_caption_styles():
    """Print available caption style presets."""
    print(f"Available caption styles ({len(CAPTION_STYLES)} total):\n")
    for name, style in CAPTION_STYLES.items():
        default = " (default)" if name == DEFAULT_CAPTION_STYLE else ""
        print(f"  {name:<15} {style['description']}{default}")


if __name__ == "__main__":
    main()
