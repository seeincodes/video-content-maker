"""AI script rewriter — transforms dry/academic text into punchy brainrot narration."""

from __future__ import annotations

import logging
import os
import random
import re

logger = logging.getLogger(__name__)

REWRITE_MODES: dict[str, str] = {
    "brainrot": "Gen-Z brainrot style — short punchy sentences, slang, hype energy",
    "educational": "Clear educational tone — engaging but informative, like a good teacher",
    "dramatic": "Dramatic storytelling — suspense, cliffhangers, emotional hooks",
    "none": "No rewriting — use the original text as-is",
}

DEFAULT_REWRITE_MODE = "none"

_SYSTEM_PROMPT = """You are a script rewriter for short-form video content. \
Your job is to rewrite dry/academic/boring text into engaging narration scripts \
that keep viewers watching.

Rules:
- Keep ALL the factual information from the original
- Output ONLY the rewritten narration text (no headings, bullets, or formatting)
- Keep it concise — aim for roughly the same word count
- No emojis in the output (they can't be spoken by TTS)
- Write in a way that sounds natural when spoken aloud"""

_STYLE_PROMPTS = {
    "brainrot": (
        "Rewrite this in Gen-Z brainrot style: short punchy sentences, use slang "
        "(bro, fr, no cap, lowkey, deadass, ngl, ong), hype energy, "
        "conversational tone like you're explaining to a friend. "
        "Make it sound like a viral TikTok voiceover."
    ),
    "educational": (
        "Rewrite this in an engaging educational style: clear and concise, "
        "use analogies and relatable comparisons, rhetorical questions to hook attention, "
        "varied sentence length for rhythm. Think Kurzgesagt or Veritasium narration."
    ),
    "dramatic": (
        "Rewrite this in a dramatic storytelling style: build suspense, "
        "use cliffhanger transitions, emotional hooks, vivid imagery, "
        "short impactful sentences mixed with longer flowing ones. "
        "Think documentary narrator meets thriller."
    ),
}

# Brainrot vocabulary for local fallback
_BRAINROT_INTROS = [
    "Bro listen up.",
    "Okay so check this out.",
    "No cap, this is wild.",
    "Ngl this is actually insane.",
    "Yo, let me put you on.",
    "Alright lock in for this one.",
    "Fr fr, you need to hear this.",
]

_BRAINROT_TRANSITIONS = [
    "And here's where it gets crazy —",
    "But wait, it gets even crazier.",
    "Bro. It doesn't stop there.",
    "Now here's the thing though.",
    "And get this —",
    "Deadass though,",
    "No but fr,",
]

_BRAINROT_EMPHASIS = [
    "like actually",
    "deadass",
    "no cap",
    "fr fr",
    "lowkey",
    "literally",
    "on god",
]


def _local_brainrot_rewrite(text: str) -> str:
    """Simple local brainrot rewrite without requiring an API key.

    Applies basic transformations: adds intros, transitions, and filler words.
    Not as good as GPT but works offline and free.
    """
    rng = random.Random(42)

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text

    result_parts = []

    # Add intro
    result_parts.append(rng.choice(_BRAINROT_INTROS))

    for i, sentence in enumerate(sentences):
        # Add transition between some sentences
        if i > 0 and i % 3 == 0 and i < len(sentences) - 1:
            result_parts.append(rng.choice(_BRAINROT_TRANSITIONS))

        # Occasionally add emphasis words
        if rng.random() < 0.3 and len(sentence.split()) > 5:
            words = sentence.split()
            insert_pos = rng.randint(1, min(3, len(words) - 1))
            words.insert(insert_pos, rng.choice(_BRAINROT_EMPHASIS))
            sentence = " ".join(words)

        result_parts.append(sentence)

    return " ".join(result_parts)


def _local_educational_rewrite(text: str) -> str:
    """Simple local educational rewrite — adds hooks and transitions."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text

    hooks = [
        "Here's something fascinating:",
        "Think about this for a moment.",
        "Now, this is where it gets interesting.",
        "Consider this:",
        "What's remarkable is —",
    ]
    rng = random.Random(42)
    result_parts = []

    for i, sentence in enumerate(sentences):
        if i == 0:
            result_parts.append(rng.choice(hooks))
        elif i % 4 == 0 and i < len(sentences) - 1:
            result_parts.append(rng.choice(hooks))
        result_parts.append(sentence)

    return " ".join(result_parts)


def _local_dramatic_rewrite(text: str) -> str:
    """Simple local dramatic rewrite — adds suspense."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return text

    dramatic_transitions = [
        "But then —",
        "And what happened next changed everything.",
        "Nobody expected what came next.",
        "The truth? Far stranger than fiction.",
        "And here's where the story takes a turn.",
    ]
    rng = random.Random(42)
    result_parts = []

    for i, sentence in enumerate(sentences):
        if i > 0 and i % 3 == 0 and i < len(sentences) - 1:
            result_parts.append(rng.choice(dramatic_transitions))
        result_parts.append(sentence)

    return " ".join(result_parts)


_LOCAL_REWRITERS = {
    "brainrot": _local_brainrot_rewrite,
    "educational": _local_educational_rewrite,
    "dramatic": _local_dramatic_rewrite,
}


def rewrite_script(text: str, mode: str = "none") -> str:
    """Rewrite text into the specified narration style.

    Uses OpenAI API if OPENAI_API_KEY is set; falls back to local transformations.

    Args:
        text: The original text to rewrite.
        mode: One of the REWRITE_MODES keys.

    Returns:
        The rewritten text (or original if mode is 'none').
    """
    if mode == "none" or mode not in REWRITE_MODES:
        return text

    # Try OpenAI API first
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return _rewrite_with_openai(text, mode, api_key)
        except Exception as e:
            logger.warning("OpenAI rewrite failed, using local fallback: %s", e)

    # Local fallback
    rewriter = _LOCAL_REWRITERS.get(mode)
    if rewriter:
        logger.info("Using local %s rewriter (no OPENAI_API_KEY set)", mode)
        return rewriter(text)

    return text


def _rewrite_with_openai(text: str, mode: str, api_key: str) -> str:
    """Rewrite using OpenAI chat completion API."""
    import requests

    style_prompt = _STYLE_PROMPTS[mode]
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"{style_prompt}\n\nOriginal text:\n{text}"},
    ]

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": len(text.split()) * 3,
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"].strip()
