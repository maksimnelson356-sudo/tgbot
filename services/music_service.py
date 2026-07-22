"""Music search and download via JioSaavn API."""

import io
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class MusicTrack:
    track_id: str
    title: str
    artist: str
    duration: int
    download_url: str
    image_url: str


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search JioSaavn for tracks."""
    url = "https://www.jiosaavn.com/api.php"
    params = {
        "__call": "search.getResults",
        "query": query,
        "p": "1",
        "n": str(limit),
        "includeMetaTags": "1",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning("JioSaavn search failed: %d", resp.status)
                    return []

                data = await resp.json()
                results = data.get("results", [])
                tracks = []

                for t in results:
                    track_id = t.get("id", "")
                    title = _clean_html(t.get("song", "Unknown"))
                    artist = _clean_html(t.get("primary_artists", t.get("singers", "Unknown")))
                    duration = int(t.get("duration", 0))
                    image = t.get("image", "")

                    # Build download URL from song key
                    encrypted_url = t.get("encrypted_media_url", "")
                    if encrypted_url:
                        dl_url = f"https://www.jiosaavn.com/api.php?__call=song.validateUrl&__={encrypted_url}"
                    else:
                        dl_url = ""

                    tracks.append(MusicTrack(
                        track_id=track_id,
                        title=title,
                        artist=artist,
                        duration=duration,
                        download_url=dl_url,
                        image_url=image,
                    ))

                return tracks

    except Exception as e:
        logger.warning("JioSaavn search error: %s", e)
        return []


async def download_track(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download full track from JioSaavn."""
    if not track.download_url:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            # First get the validated URL
            async with session.get(track.download_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                media_url = data.get("results", {}).get("media_url", "")
                if not media_url:
                    return None
                media_url = unquote(media_url)

            # Download the actual audio
            async with session.get(media_url) as resp:
                if resp.status != 200:
                    return None
                audio_data = await resp.read()
                if len(audio_data) < 10000:
                    return None

                buf = io.BytesIO(audio_data)
                buf.name = f"{track.artist} - {track.title}.mp4"
                return buf

    except Exception as e:
        logger.warning("JioSaavn download error: %s", e)
        return None
