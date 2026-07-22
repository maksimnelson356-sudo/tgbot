"""Music search and download via yt-dlp (YouTube)."""

import io
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MAX_DURATION = 600  # 10 minutes in seconds
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB (Telegram limit)


@dataclass
class MusicResult:
    audio: io.BytesIO
    title: str
    duration: int
    url: str


async def search_and_download(query: str) -> Optional[MusicResult]:
    """Search YouTube for a query and download audio of the first result.

    Returns MusicResult or None if nothing found / error.
    """
    import yt_dlp

    def _search_and_download() -> Optional[MusicResult]:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "audio")

            ydl_opts = {
                "default_search": "ytsearch1",
                "format": "bestaudio/best",
                "outtmpl": output_path,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 30,
                "extractor_args": {
                    "youtube": {"player_client": ["ios", "web"]},
                },
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                    if not info or not info.get("entries"):
                        return None

                    entry = info["entries"][0]
                    if entry is None:
                        return None

                    title = entry.get("title", "Unknown")
                    duration = entry.get("duration", 0) or 0
                    url = entry.get("webpage_url", "")

                    # Find the downloaded file
                    mp3_path = output_path + ".mp3"
                    if not os.path.exists(mp3_path):
                        # Try other extensions
                        for ext in ("mp3", "opus", "ogg", "wav"):
                            candidate = output_path + f".{ext}"
                            if os.path.exists(candidate):
                                mp3_path = candidate
                                break

                    if not os.path.exists(mp3_path):
                        return None

                    file_size = os.path.getsize(mp3_path)
                    if file_size > MAX_FILE_SIZE:
                        return None

                    with open(mp3_path, "rb") as f:
                        audio_data = f.read()

                    audio_buf = io.BytesIO(audio_data)
                    audio_buf.name = f"{title[:50]}.mp3"
                    return MusicResult(
                        audio=audio_buf,
                        title=title,
                        duration=duration,
                        url=url,
                    )

            except Exception as e:
                if "No results" in str(e) or "Match failed" in str(e):
                    logger.info("No results for query: %s", query)
                else:
                    logger.warning("Music download error: %s", e)
                return None

    loop = __import__("asyncio").get_event_loop()
    return await loop.run_in_executor(None, _search_and_download)
