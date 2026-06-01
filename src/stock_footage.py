"""Stock footage fetching from Pexels API with Ken Burns animation for photos."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path

import numpy as np
import requests
from moviepy import ImageClip, VideoFileClip, concatenate_videoclips

from .config import ASSETS_DIR, VIDEO_HEIGHT, VIDEO_WIDTH

logger = logging.getLogger(__name__)

PEXELS_API_URL = "https://api.pexels.com"
CACHE_DIR = ASSETS_DIR / "pexels_cache"

# Common words to strip when extracting search keywords
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could must need dare ought to of in for on with at "
    "by from as into through during before after above below between out off over "
    "under again further then once here there when where why how all each every both "
    "few more most other some such no nor not only own same so than too very just "
    "don t s it its he she they them their his her my your our this that these those "
    "and but or if while because although though even also still already yet about up "
    "what which who whom whose i me we you him us let get got like one two really "
    "thing things something anything everything nothing much many well way make makes "
    "made know knows knew think thinks thought go goes went come comes came see sees "
    "saw take takes took give gives gave find finds found tell tells told ask asks "
    "asked use uses used try tries tried keep keeps kept say says said called bro "
    "listen gonna fr".split()
)


def get_api_key() -> str | None:
    """Retrieve the Pexels API key from environment."""
    return os.environ.get("PEXELS_API_KEY")


def extract_keywords(text: str, max_keywords: int = 3) -> str:
    """Extract the most relevant search keywords from a text segment.

    Uses simple frequency-based keyword extraction after removing stopwords.
    """
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    filtered = [w for w in words if w not in _STOPWORDS]
    if not filtered:
        filtered = words[:max_keywords] if words else ["abstract"]

    # Score by frequency, prefer longer words (more specific)
    freq: dict[str, float] = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1.0 + len(w) * 0.1

    ranked = sorted(freq, key=lambda w: freq[w], reverse=True)
    return " ".join(ranked[:max_keywords])


def _cache_path(url: str, ext: str) -> Path:
    """Generate a deterministic cache path for a URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{url_hash}{ext}"


def search_pexels_videos(
    query: str,
    api_key: str,
    per_page: int = 5,
    orientation: str = "portrait",
) -> list[dict]:
    """Search Pexels for videos matching the query."""
    resp = requests.get(
        f"{PEXELS_API_URL}/videos/search",
        headers={"Authorization": api_key},
        params={
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
            "size": "medium",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("videos", [])


def search_pexels_photos(
    query: str,
    api_key: str,
    per_page: int = 5,
    orientation: str = "portrait",
) -> list[dict]:
    """Search Pexels for photos matching the query (fallback when no videos found)."""
    resp = requests.get(
        f"{PEXELS_API_URL}/v1/search",
        headers={"Authorization": api_key},
        params={
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
            "size": "medium",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("photos", [])


def _pick_best_video_file(video: dict) -> str | None:
    """Select the best-quality video file URL from a Pexels video entry."""
    files = video.get("video_files", [])
    # Prefer HD portrait files
    portrait_files = [
        f for f in files
        if f.get("height", 0) >= f.get("width", 0) and f.get("height", 0) >= 720
    ]
    if portrait_files:
        portrait_files.sort(key=lambda f: f.get("height", 0), reverse=True)
        return portrait_files[0].get("link")

    # Fallback to highest resolution
    if files:
        files.sort(key=lambda f: f.get("height", 0), reverse=True)
        return files[0].get("link")
    return None


def download_file(url: str, dest: Path) -> Path:
    """Download a file to dest, using cache if available."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest


def _apply_ken_burns(
    image_path: Path,
    duration: float,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = 30,
    zoom_start: float = 1.0,
    zoom_end: float = 1.2,
    pan_direction: str = "right",
) -> ImageClip:
    """Apply Ken Burns effect (slow zoom + pan) to a static image."""
    from PIL import Image

    img = Image.open(image_path).convert("RGB")

    # Scale image so it's large enough to crop from at max zoom
    max_zoom = max(zoom_start, zoom_end)
    target_w = int(width * max_zoom * 1.1)
    target_h = int(height * max_zoom * 1.1)

    # Resize maintaining aspect ratio, then center-crop
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h
    if img_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    img_arr = np.array(img)

    cx = new_w / 2.0
    cy = new_h / 2.0

    # Pan offset range
    max_pan = (new_w - width * max_zoom) / 2.0
    if max_pan < 0:
        max_pan = 0

    def make_frame(t: float) -> np.ndarray:
        progress = t / duration if duration > 0 else 0
        zoom = zoom_start + (zoom_end - zoom_start) * progress

        crop_w = int(width / zoom)
        crop_h = int(height / zoom)

        # Pan
        if pan_direction == "right":
            offset_x = max_pan * progress
        elif pan_direction == "left":
            offset_x = -max_pan * progress
        else:
            offset_x = 0

        x1 = int(cx + offset_x - crop_w / 2)
        y1 = int(cy - crop_h / 2)

        # Clamp
        x1 = max(0, min(x1, new_w - crop_w))
        y1 = max(0, min(y1, new_h - crop_h))

        crop = img_arr[y1 : y1 + crop_h, x1 : x1 + crop_w]

        # Resize crop to target dimensions
        cropped_img = Image.fromarray(crop)
        resized = cropped_img.resize((width, height), Image.LANCZOS)
        return np.array(resized)

    from moviepy import VideoClip

    clip = VideoClip(make_frame, duration=duration)
    return clip.with_fps(fps)


def fetch_stock_footage_clips(
    text_segments: list[dict],
    api_key: str,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = 30,
) -> list[tuple[str, object]]:
    """Fetch stock footage for each text segment.

    Args:
        text_segments: List of dicts with 'text', 'start_s', 'end_s' keys.
        api_key: Pexels API key.
        width: Video width.
        height: Video height.
        fps: Frames per second.

    Returns:
        List of (query, VideoClip) tuples for each segment.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    clips: list[tuple[str, object]] = []
    pan_directions = ["right", "left", "right", "left"]
    used_queries: set[str] = set()

    for i, seg in enumerate(text_segments):
        query = extract_keywords(seg["text"])
        duration = seg["end_s"] - seg["start_s"]
        if duration <= 0:
            continue

        # Avoid duplicate searches
        if query in used_queries:
            query = query + " nature"
        used_queries.add(query)

        clip = None
        logger.info("Segment %d: searching Pexels for '%s' (%.1fs)", i, query, duration)

        # Try videos first
        try:
            videos = search_pexels_videos(query, api_key, per_page=3)
            for video in videos:
                video_url = _pick_best_video_file(video)
                if not video_url:
                    continue
                cache = _cache_path(video_url, ".mp4")
                try:
                    download_file(video_url, cache)
                    vc = VideoFileClip(str(cache))
                    # Resize to fit
                    clip = _resize_clip(vc, width, height)
                    # Trim or loop
                    if clip.duration >= duration:
                        clip = clip.subclipped(0, duration)
                    else:
                        n = int(duration / clip.duration) + 1
                        clip = concatenate_videoclips([clip] * n).subclipped(0, duration)
                    clip = clip.with_fps(fps)
                    break
                except Exception as e:
                    logger.warning("Failed to load video for '%s': %s", query, e)
                    continue
        except Exception as e:
            logger.warning("Pexels video search failed for '%s': %s", query, e)

        # Fall back to photos with Ken Burns
        if clip is None:
            try:
                photos = search_pexels_photos(query, api_key, per_page=3)
                for photo in photos:
                    src = photo.get("src", {})
                    photo_url = src.get("large2x") or src.get("original")
                    if not photo_url:
                        continue
                    ext = ".jpg"
                    cache = _cache_path(photo_url, ext)
                    try:
                        download_file(photo_url, cache)
                        pan_dir = pan_directions[i % len(pan_directions)]
                        clip = _apply_ken_burns(
                            cache,
                            duration,
                            width,
                            height,
                            fps,
                            zoom_start=1.0,
                            zoom_end=1.15,
                            pan_direction=pan_dir,
                        )
                        break
                    except Exception as e:
                        logger.warning("Failed to load photo for '%s': %s", query, e)
                        continue
            except Exception as e:
                logger.warning("Pexels photo search failed for '%s': %s", query, e)

        if clip is not None:
            clips.append((query, clip))
        else:
            logger.warning("No stock footage found for '%s', will use fallback", query)

    return clips


def _resize_clip(clip: VideoFileClip, width: int, height: int) -> VideoFileClip:
    """Resize a video clip to fill the target dimensions (crop to 9:16)."""
    clip_ratio = clip.w / clip.h
    target_ratio = width / height

    if clip_ratio > target_ratio:
        clip = clip.resized(height=height)
        x_center = clip.w / 2
        x1 = int(x_center - width / 2)
        clip = clip.cropped(x1=x1, x2=x1 + width)
    else:
        clip = clip.resized(width=width)
        y_center = clip.h / 2
        y1 = int(y_center - height / 2)
        clip = clip.cropped(y1=y1, y2=y1 + height)
    return clip


def build_stock_footage_background(
    text: str,
    word_timings: list,
    duration: float,
    api_key: str,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = 30,
    words_per_scene: int = 15,
) -> object | None:
    """Build a composite background from stock footage matching text content.

    Splits the narration into scenes, fetches relevant footage for each,
    and concatenates them into a single background clip.

    Args:
        text: The full narration text.
        word_timings: List of WordTiming objects from TTS.
        duration: Total video duration in seconds.
        api_key: Pexels API key.
        width: Video width.
        height: Video height.
        fps: Frames per second.
        words_per_scene: How many words per scene/segment.

    Returns:
        A VideoClip composited from stock footage, or None if no footage found.
    """
    if not word_timings:
        return None

    # Split word timings into scenes
    segments = []
    for i in range(0, len(word_timings), words_per_scene):
        chunk = word_timings[i : i + words_per_scene]
        if not chunk:
            continue
        seg_text = " ".join(w.word for w in chunk)
        segments.append({
            "text": seg_text,
            "start_s": chunk[0].start_s,
            "end_s": chunk[-1].end_s,
        })

    # Extend last segment to cover full duration
    if segments:
        segments[-1]["end_s"] = duration

    logger.info("Split text into %d scenes for stock footage", len(segments))

    results = fetch_stock_footage_clips(segments, api_key, width, height, fps)

    if not results:
        return None

    # Concatenate all clips
    all_clips = [clip for _, clip in results]
    if len(all_clips) == 1:
        final = all_clips[0]
    else:
        final = concatenate_videoclips(all_clips)

    # Ensure it covers the full duration
    if final.duration < duration:
        # Loop last clip to fill
        gap = duration - final.duration
        last_clip = all_clips[-1]
        if last_clip.duration > 0:
            n = int(gap / last_clip.duration) + 1
            filler = concatenate_videoclips([last_clip] * n).subclipped(0, gap)
            final = concatenate_videoclips([final, filler])

    final = final.subclipped(0, min(final.duration, duration))
    return final.with_fps(fps)
