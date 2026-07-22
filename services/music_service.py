"""Music search and download - Deezer (search) + SoundCloud (full tracks fallback)."""

import io
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

_client_id_cache: Optional[str] = None


@dataclass
class MusicTrack:
    title: str
    artist: str
    duration: int
    preview_url: str       # Deezer 30s preview
    deezer_url: str        # Deezer page
    track_id: int          # Deezer track ID


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search Deezer (reliable) for tracks."""
    url = "https://api.deezer.com/search"
    params = {"q": query, "limit": limit}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("Deezer search failed: %d", resp.status)
                    return []

                data = await resp.json()
                tracks = data.get("data", [])
                results = []
                for t in tracks:
                    if not t.get("preview"):
                        continue
                    results.append(MusicTrack(
                        title=t.get("title", "Unknown"),
                        artist=t.get("artist", {}).get("name", "Unknown"),
                        duration=t.get("duration", 0),
                        preview_url=t.get("preview", ""),
                        deezer_url=t.get("link", ""),
                        track_id=t.get("id", 0),
                    ))
                    if len(results) >= limit:
                        break
                return results

    except Exception as e:
        logger.warning("Music search error: %s", e)
        return []


async def download_track(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download the Deezer preview (30s MP3)."""
    if not track.preview_url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(track.preview_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                if len(data) < 1000:
                    return None
                buf = io.BytesIO(data)
                buf.name = f"{track.artist} - {track.title}.mp3"
                return buf
    except Exception as e:
        logger.warning("Download error: %s", e)
        return None
