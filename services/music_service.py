"""Music search and download via Deezer API."""

import io
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

DEEZER_SEARCH_URL = "https://api.deezer.com/search"


@dataclass
class MusicResult:
    audio: io.BytesIO
    title: str
    artist: str
    duration: int
    url: str


async def search_and_download(query: str) -> Optional[MusicResult]:
    """Search Deezer and download 30s preview MP3."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                DEEZER_SEARCH_URL,
                params={"q": query, "limit": 5},
            ) as resp:
                if resp.status != 200:
                    logger.warning("Deezer search failed: status %d", resp.status)
                    return None

                data = await resp.json()
                tracks = data.get("data", [])
                if not tracks:
                    return None

                for track in tracks:
                    preview_url = track.get("preview", "")
                    if not preview_url:
                        continue

                    async with session.get(preview_url) as audio_resp:
                        if audio_resp.status != 200:
                            continue

                        audio_data = await audio_resp.read()
                        if len(audio_data) < 1000:
                            continue

                        audio_buf = io.BytesIO(audio_data)
                        artist = track.get("artist", {}).get("name", "Unknown")
                        title = track.get("title", "Unknown")
                        audio_buf.name = f"{artist} - {title}.mp3"

                        return MusicResult(
                            audio=audio_buf,
                            title=title,
                            artist=artist,
                            duration=track.get("duration", 0),
                            url=track.get("link", ""),
                        )

                return None

    except Exception as e:
        logger.warning("Music search error: %s", e)
        return None
