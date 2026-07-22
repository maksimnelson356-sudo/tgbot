"""Music search via Deezer API."""

import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

DEEZER_SEARCH_URL = "https://api.deezer.com/search"


@dataclass
class MusicResult:
    title: str
    artist: str
    duration: int
    preview_url: str
    url: str


async def search(query: str) -> Optional[MusicResult]:
    """Search Deezer for a query. Returns first result or None."""
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
                return MusicResult(
                    title=track.get("title", "Unknown"),
                    artist=track.get("artist", {}).get("name", "Unknown"),
                    duration=track.get("duration", 0),
                    preview_url=track.get("preview", ""),
                    url=track.get("link", ""),
                )

    except Exception as e:
        logger.warning("Music search error: %s", e)
        return None
