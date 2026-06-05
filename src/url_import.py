"""URL/article import — extract readable text from a web page."""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser

import requests

logger = logging.getLogger(__name__)

# Tags whose text content we want
_CONTENT_TAGS = frozenset({
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "td", "th", "blockquote", "figcaption",
})

# Tags to completely skip (including their children)
_SKIP_TAGS = frozenset({
    "script", "style", "nav", "footer", "header", "aside",
    "form", "button", "iframe", "noscript", "svg",
})


class _ArticleExtractor(HTMLParser):
    """Simple HTML parser that extracts text from content-bearing tags."""

    def __init__(self):
        super().__init__()
        self.paragraphs: list[str] = []
        self._current_text: list[str] = []
        self._in_content_tag = 0
        self._skip_depth = 0
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        self._tag_stack.append(tag)

        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            return

        if tag in _CONTENT_TAGS:
            self._in_content_tag += 1
            self._current_text = []

    def handle_endtag(self, tag: str):
        tag = tag.lower()

        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        if self._skip_depth > 0:
            return

        if tag in _CONTENT_TAGS:
            self._in_content_tag = max(0, self._in_content_tag - 1)
            text = " ".join(self._current_text).strip()
            if text and len(text) > 20:
                self.paragraphs.append(text)
            self._current_text = []

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        if self._in_content_tag > 0:
            cleaned = data.strip()
            if cleaned:
                self._current_text.append(cleaned)


def extract_text_from_url(url: str) -> str:
    """Fetch a URL and extract the article text.

    Args:
        url: The web page URL to extract text from.

    Returns:
        Extracted article text (paragraphs joined with spaces).

    Raises:
        ValueError: If URL is invalid or no text could be extracted.
        requests.RequestException: If the HTTP request fails.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    logger.info("Fetching URL: %s", url)

    resp = requests.get(
        url,
        timeout=15,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; BrainrotGenerator/1.0; "
                "+https://github.com/seeincodes/video-content-maker)"
            ),
        },
    )
    resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise ValueError(f"URL returned unsupported content type: {content_type}")

    # If plain text, return directly
    if "text/plain" in content_type:
        return resp.text.strip()

    # Parse HTML
    parser = _ArticleExtractor()
    parser.feed(resp.text)

    if not parser.paragraphs:
        raise ValueError("Could not extract article text from the URL.")

    # Join paragraphs into a single text block
    text = " ".join(parser.paragraphs)

    # Clean up excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()

    logger.info("Extracted %d characters from URL", len(text))
    return text
