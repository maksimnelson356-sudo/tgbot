"""Music search and download via SoundCloud."""

import io
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

_client_id_cache: Optional[str] = None


async def _get_client_id(session: aiohttp.ClientSession) -> Optional[str]:
    """Extract client_id from SoundCloud JS bundles."""
    global _client_id_cache
    if _client_id_cache:
        return _client_id_cache

    try:
        # Get the main page to find JS bundle URLs
        async with session.get("https://soundcloud.com") as resp:
            if resp.status != 200:
                return None
            html = await resp.text()

        # Find JS bundle URLs
        js_urls = re.findall(r'(https://a\.sndcdn\.com/assets/app[^"]+\.js)', html)
        if not js_urls:
            return None

        # Check bundles for client_id
        for js_url in js_urls[:3]:
            async with session.get(js_url) as resp:
                if resp.status != 200:
                    continue
                js_text = await resp.text()
                # Look for client_id pattern
                match = re.search(r'client_id:"([a-zA-Z0-9]{32})"', js_text)
                if match:
                    _client_id_cache = match.group(1)
                    logger.info("Extracted SoundCloud client_id: %s...", _client_id_cache[:8])
                    return _client_id_cache

        return None
    except Exception as e:
        logger.warning("Failed to get SoundCloud client_id: %s", e)
        return None


@dataclass
class MusicTrack:
    track_id: int
    title: str
    artist: str
    duration: int
    stream_url: str
    permalink_url: str


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search SoundCloud for tracks."""
    async with aiohttp.ClientSession() as session:
        client_id = await _get_client_id(session)
        if not client_id:
            logger.warning("No SoundCloud client_id available")
            return []

        url = "https://api-v2.soundcloud.com/search/tracks"
        params = {"q": query, "limit": limit, "client_id": client_id}

        try:
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
                    track_auth = t.get("track_authorization", "")
                    permalink = t.get("permalink_url", "")

                    results.append(MusicTrack(
                        track_id=track_id,
                        title=title,
                        artist=artist,
                        duration=duration,
                        stream_url=track_auth,
                        permalink_url=permalink,
                    ))

                    if len(results) >= limit:
                        break

                return results

        except Exception as e:
            logger.warning("SoundCloud search error: %s", e)
            return []


async def download_track(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download full track from SoundCloud."""
    async with aiohttp.ClientSession() as session:
        client_id = await _get_client_id(session)
        if not client_id:
            return None

        try:
            api_url = f"https://api-v2.soundcloud.com/tracks/{track.track_id}/stream"
            params = {"client_id": client_id, "trackAuthorization": track.stream_url}

            async with session.get(api_url, params=params) as resp:
                if resp.status != 200:
                    logger.warning("SoundCloud stream API failed: %d", resp.status)
                    return None

                stream_data = await resp.json()
                redirect_url = stream_data.get("url")
                if not redirect_url:
                    logger.warning("No stream URL in SoundCloud response")
                    return None

                async with session.get(redirect_url) as audio_resp:
                    if audio_resp.status != 200:
                        return None

                    data = await audio_resp.read()
                    if len(data) < 10000:
                        return None

                    buf = io.BytesIO(data)
                    buf.name = f"{track.artist} - {track.title}.mp3"
                    return buf

        except Exception as e:
            logger.warning("SoundCloud download error: %s", e)
            return None
