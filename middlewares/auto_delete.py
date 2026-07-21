from aiogram import BaseMiddleware
from aiogram.types import Message


# Known menu buttons that should be auto-deleted in groups
_MENU_TEXTS = {
    "🎮 Games", "🎮 Игры",
    "😂 Joke", "😂 Шутка",
    "🧠 Fact", "🧠 Факт",
    "🎲 Dice", "🎲 Кубик",
    "📊 Stats", "📊 Статистика",
    "❓ Help", "❓ Помощь",
    "🔙 Back", "🔙 Назад",
    "🪨 RPS", "🔢 Guess", "🧠 Trivia",
    "🎯 Dart",
}


class AutoDeleteCommandsMiddleware(BaseMiddleware):
    """Automatically delete command and menu messages after processing."""

    async def __call__(self, handler, event: Message, data: dict):
        result = await handler(event, data)

        if event.chat.type in ("group", "supergroup") and event.text:
            if event.text.startswith("/") or event.text in _MENU_TEXTS:
                try:
                    await event.delete()
                except Exception:
                    pass

        return result
