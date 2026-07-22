"""Music search and download via Hitmo (parses HTML)."""

import io
import logging
import re
from dataclasses import dataclass
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HITMO_MIRRORS = [
    "https://rus.hitmotop.com",
    "https://hitmoz.org",
    "https://hitmotop.com",
]


@dataclass
class MusicTrack:
    title: str
    artist: str
    duration: str
    download_url: str
    image_url: str


async def _try_mirror(base_url: str, query: str, limit: int, session: aiohttp.ClientSession) -> list[MusicTrack]:
    """Try searching on a single mirror."""
    search_url = f"{base_url}/search"
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    try:
        async with session.get(search_url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.info("Hitmo mirror %s returned %d", base_url, resp.status)
                return []

            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            results = []
            items = soup.select(".track__wrapper, .tracks__item, .song-item, .item-song")

            for item in items[:limit]:
                # Try multiple selectors for title/artist
                title_el = item.select_one(".track__title, .song-title, .title")
                artist_el = item.select_one(".track__desc, .artist-name, .artist")
                time_el = item.select_one(".track__time, .song-duration, .duration")
                img_el = item.select_one("img")
                dl_el = item.select_one('a[href*="/download/"], a.track__download-btn, a[download]')

                if not dl_el:
                    continue

                title = title_el.get_text(strip=True) if title_el else "Unknown"
                artist = artist_el.get_text(strip=True) if artist_el else "Unknown"
                duration = time_el.get_text(strip=True) if time_el else "?"
                dl_url = dl_el.get("href", "")
                img_url = img_el.get("src", img_el.get("data-src", "")) if img_el else ""

                if dl_url and not dl_url.startswith("http"):
                    dl_url = base_url + dl_url

                results.append(MusicTrack(
                    title=title,
                    artist=artist,
                    duration=duration,
                    download_url=dl_url,
                    image_url=img_url,
                ))

            return results

    except Exception as e:
        logger.info("Hitmo mirror %s error: %s", base_url, e)
        return []


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search Hitmo across mirrors."""
    async with aiohttp.ClientSession() as session:
        for mirror in HITMO_MIRRORS:
            results = await _try_mirror(mirror, query, limit, session)
            if results:
                logger.info("Found %d results on %s", len(results), mirror)
                return results

        logger.warning("No results from any Hitmo mirror")
        return []


async def download_track(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download track from Hitmo using session with cookies."""
    if not track.download_url:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Referer": "https://rus.hitmotop.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Visit main page to get cookies
            async with session.get("https://rus.hitmotop.com/", timeout=aiohttp.ClientTimeout(total=10)):
                pass

            async with session.get(track.download_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.warning("Download failed: %d (url: %s)", resp.status, track.download_url)
                    return None

                content_type = resp.headers.get("Content-Type", "")
                data = await resp.read()
                if len(data) < 10000:
                    logger.warning("Downloaded file too small: %d bytes", len(data))
                    return None

                # Determine extension from content type
                ext = "mp3"
                if "mpegurl" in content_type or ".m3u" in (resp.url.path if hasattr(resp.url, 'path') else ""):
                    # It's an M3U playlist, need to download the actual file
                    playlist_text = data.decode("utf-8", errors="ignore")
                    m3u_match = re.search(r"(https?://\S+\.(?:mp3|m4a|ogg))", playlist_text)
                    if m3u_match:
                        async with session.get(m3u_match.group(1)) as resp2:
                            if resp2.status == 200:
                                data = await resp2.read()

                buf = io.BytesIO(data)
                buf.name = f"{track.artist} - {track.title}.mp3"
                return buf

    except Exception as e:
        logger.warning("Download error: %s", e)
        return None
