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
    """Search Deezer for a query and download the preview of the first result.

    Returns MusicResult or None if nothing found / error.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                DEEZER_SEARCH_URL,
                params={"q": query, "limit": 1},
            ) as resp:
                if resp.status != 200:
                    logger.warning("Deezer search failed: status %d", resp.status)
                    return None

                data = await resp.json()
                tracks = data.get("data", [])
                if not tracks:
                    return None

                track = tracks[0]
                title = track.get("title", "Unknown")
                artist = track.get("artist", {}).get("name", "Unknown")
                duration = track.get("duration", 0)
                preview_url = track.get("preview", "")
                link = track.get("link", "")

                if not preview_url:
                    logger.warning("No preview URL for track: %s - %s", artist, title)
                    return None

                async with session.get(preview_url) as audio_resp:
                    if audio_resp.status != 200:
                        logger.warning("Failed to download preview: status %d", audio_resp.status)
                        return None

                    audio_data = await audio_resp.read()
                    if len(audio_data) < 1000:
                        logger.warning("Preview too small, likely invalid")
                        return None

                    audio_buf = io.BytesIO(audio_data)
                    audio_buf.name = f"{artist} - {title}.mp3"
                    return MusicResult(
                        audio=audio_buf,
                        title=title,
                        artist=artist,
                        duration=duration,
                        url=link,
                    )

    except Exception as e:
        logger.warning("Music search error: %s", e)
        return None
