"""Music search and download via SoundCloud API."""

import io
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class MusicTrack:
    track_id: int
    title: str
    artist: str
    duration: int
    stream_url: str
    permalink_url: str


SOUNDCLOUD_CLIENT_ID = "a3e05fcd8b32746d0b06a49456740760"


async def _get_client_id() -> str:
    """Try to get fresh client_id from SoundCloud website."""
    return SOUNDCLOUD_CLIENT_ID


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search SoundCloud for tracks."""
    client_id = await _get_client_id()
    url = "https://api-v2.soundcloud.com/search/tracks"
    params = {
        "q": query,
        "limit": limit,
        "client_id": client_id,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("SoundCloud search failed: %d", resp.status)
                    return []

                data = await resp.json()
                collection = data.get("collection", [])

                results = []
                for t in collection:
                    if not t.get("streamable"):
                        continue
                    track_id = t.get("id", 0)
                    title = t.get("title", "Unknown")
                    artist = t.get("user", {}).get("username", "Unknown")
                    duration_ms = t.get("duration", 0)
                    duration = duration_ms // 1000
                    permalink = t.get("permalink_url", "")

                    results.append(MusicTrack(
                        track_id=track_id,
                        title=title,
                        artist=artist,
                        duration=duration,
                        stream_url="",
                        permalink_url=permalink,
                    ))

                return results

    except Exception as e:
        logger.warning("SoundCloud search error: %s", e)
        return []


async def download_track(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download full track from SoundCloud."""
    client_id = await _get_client_id()

    # Get stream URL
    api_url = f"https://api-v2.soundcloud.com/tracks/{track.track_id}/stream"
    params = {"client_id": client_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, allow_redirects=True) as resp:
                if resp.status != 200:
                    logger.warning("SoundCloud stream failed: %d", resp.status)
                    return None

                audio_data = await resp.read()
                if len(audio_data) < 10000:
                    logger.warning("SoundCloud track too small, likely error")
                    return None

                buf = io.BytesIO(audio_data)
                buf.name = f"{track.artist} - {track.title}.mp3"
                return buf

    except Exception as e:
        logger.warning("SoundCloud download error: %s", e)
        return None
