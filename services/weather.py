"""Simple weather service."""
import aiohttp


async def get_weather(city: str) -> str:
    """Get weather for a city. Uses wttr.in (no API key needed)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://wttr.in/{city}?format=%C+%t+%w+%h&lang=ru",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                text = await resp.text()
                return text.strip()
            return "Weather unavailable"
