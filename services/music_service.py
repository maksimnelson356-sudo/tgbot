"""Music search and download via Deezer API."""

import io
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

DEEZER_SEARCH_URL = "https://api.deezer.com/search"


@dataclass
class MusicTrack:
    track_id: int
    title: str
    artist: str
    duration: int
    preview_url: str
    url: str


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search Deezer, return list of tracks."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                DEEZER_SEARCH_URL,
                params={"q": query, "limit": limit},
            ) as resp:
                if resp.status != 200:
                    logger.warning("Deezer search failed: status %d", resp.status)
                    return []

                data = await resp.json()
                tracks = data.get("data", [])
                results = []
                for t in tracks:
                    if not t.get("preview"):
                        continue
                    results.append(MusicTrack(
                        track_id=t["id"],
                        title=t.get("title", "Unknown"),
                        artist=t.get("artist", {}).get("name", "Unknown"),
                        duration=t.get("duration", 0),
                        preview_url=t.get("preview", ""),
                        url=t.get("link", ""),
                    ))
                return results

    except Exception as e:
        logger.warning("Music search error: %s", e)
        return []


async def download_preview(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download 30s preview MP3 for a track."""
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
        logger.warning("Music download error: %s", e)
        return None
