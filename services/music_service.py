"""Music search and download via yt-dlp (multiple sources)."""

import io
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

import yt_dlp

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB Telegram limit


@dataclass
class MusicTrack:
    title: str
    artist: str
    duration: int
    webpage_url: str


async def search(query: str, limit: int = 5) -> list[MusicTrack]:
    """Search YouTube for tracks."""
    def _search():
        ydl_opts = {
            "default_search": f"ytsearch{limit}",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 15,
            "extractor_args": {
                "youtube": {"player_client": ["android"]},
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            if not info or not info.get("entries"):
                return []
            results = []
            for entry in info["entries"]:
                if entry is None:
                    continue
                title = entry.get("title", "Unknown")
                duration = entry.get("duration", 0) or 0
                url = entry.get("webpage_url", "")
                results.append(MusicTrack(
                    title=title,
                    artist=title.split(" - ")[0] if " - " in title else title,
                    duration=duration,
                    webpage_url=url,
                ))
            return results

    loop = __import__("asyncio").get_event_loop()
    return await loop.run_in_executor(None, _search)


async def download_track(track: MusicTrack) -> Optional[io.BytesIO]:
    """Download audio from YouTube."""
    def _download():
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "audio")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_path,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 30,
                "extractor_args": {
                    "youtube": {"player_client": ["android"]},
                },
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([track.webpage_url])

                mp3_path = output_path + ".mp3"
                if not os.path.exists(mp3_path):
                    return None

                file_size = os.path.getsize(mp3_path)
                if file_size > MAX_FILE_SIZE:
                    return None

                with open(mp3_path, "rb") as f:
                    data = f.read()

                buf = io.BytesIO(data)
                buf.name = f"{track.artist} - {track.title}.mp3"
                return buf

            except Exception as e:
                logger.warning("yt-dlp download error: %s", e)
                return None

    loop = __import__("asyncio").get_event_loop()
    return await loop.run_in_executor(None, _download)
