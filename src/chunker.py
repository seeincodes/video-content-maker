"""Long-form auto-chunking — split text into multiple short clips."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Target duration for each chunk (in words, roughly 30-60s of speech at ~2.5 words/sec)
DEFAULT_CHUNK_WORDS = 75  # ~30 seconds
MAX_CHUNK_WORDS = 150  # ~60 seconds


def chunk_text(
    text: str,
    target_words: int = DEFAULT_CHUNK_WORDS,
    max_words: int = MAX_CHUNK_WORDS,
) -> list[str]:
    """Split long text into short chunks suitable for individual videos.

    Splits on sentence boundaries, targeting ~target_words per chunk.
    Never exceeds max_words per chunk (will hard-split mid-sentence if needed).

    Args:
        text: The full text to chunk.
        target_words: Target number of words per chunk (~30s at normal speech rate).
        max_words: Maximum words per chunk before forced split.

    Returns:
        List of text chunks, each suitable for one short-form video.
    """
    text = text.strip()
    if not text:
        return []

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        # If single sentence exceeds max, force-split it
        if sentence_words > max_words:
            # Flush current chunk first
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_word_count = 0

            # Split the long sentence by word count
            words = sentence.split()
            for i in range(0, len(words), target_words):
                chunk_words = words[i: i + target_words]
                chunks.append(" ".join(chunk_words))
            continue

        # Would adding this sentence exceed target?
        if current_word_count + sentence_words > target_words and current_chunk:
            # Flush current chunk
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_word_count = 0

        current_chunk.append(sentence)
        current_word_count += sentence_words

    # Flush remaining
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Merge very short trailing chunk with previous
    if len(chunks) > 1 and len(chunks[-1].split()) < 20:
        last = chunks.pop()
        chunks[-1] = chunks[-1] + " " + last

    logger.info(
        "Chunked %d words into %d clips (avg %d words/clip)",
        len(text.split()),
        len(chunks),
        len(text.split()) // max(len(chunks), 1),
    )

    return chunks
