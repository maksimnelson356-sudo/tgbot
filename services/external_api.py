"""External API clients for jokes and facts."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def get_random_joke() -> str:
    """Fetch a random joke from an API."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://v2.jokeapi.dev/joke/Any?type=single&safe-mode",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "joke" in data:
                        return data["joke"]
                    if data.get("setup") and data.get("delivery"):
                        return f"{data['setup']}\n{data['delivery']}"
    except Exception as e:
        logger.warning("Failed to fetch joke: %s", e)

    raise ConnectionError("Could not fetch joke")


async def get_random_fact() -> str:
    """Fetch a random interesting fact."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "text" in data:
                        return data["text"]
    except Exception as e:
        logger.warning("Failed to fetch fact: %s", e)

    raise ConnectionError("Could not fetch fact")
