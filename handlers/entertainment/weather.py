from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.weather import get_weather

router = Router()
router.name = "weather"


@router.message(Command("weather"))
async def cmd_weather(message: Message) -> None:
    """Get weather. Usage: /weather <city>"""
    args = message.text.removeprefix("/weather").strip()
    if not args:
        await message.answer("Usage: /weather <city>")
        return

    msg = await message.answer(f"🌤 Loading weather for {args}...")
    try:
        weather = await get_weather(args)
        await msg.edit_text(f"🌤 <b>Weather: {args}</b>\n\n{weather}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
