"""Inline query handler — respond to inline queries with jokes, facts, and games."""

import random

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from services.external_api import get_random_fact, get_random_joke

router = Router()
router.name = "inline"

# Local caches for hot content
_jokes_cache: list[str] = []
_facts_cache: list[str] = []


async def _fill_cache() -> None:
    """Fill caches on first use."""
    global _jokes_cache, _facts_cache
    if not _jokes_cache:
        try:
            joke = await get_random_joke()
            _jokes_cache = [joke]
        except Exception:
            _jokes_cache = ["Why don't scientists trust atoms? Because they make up everything!"]
    if not _facts_cache:
        try:
            fact = await get_random_fact()
            _facts_cache = [fact]
        except Exception:
            _facts_cache = ["A day on Venus is longer than a year on Venus."]


_RPS_CHOICES = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
_RPS_RESULT = {
    ("rock", "scissors"): "Ты выиграл!",
    ("paper", "rock"): "Ты выиграл!",
    ("scissors", "paper"): "Ты выиграл!",
    ("rock", "paper"): "Ты проиграл!",
    ("paper", "scissors"): "Ты проиграл!",
    ("scissors", "rock"): "Ты проиграл!",
}


@router.inline_query()
async def handle_inline(inline_query: InlineQuery) -> None:
    """Handle inline queries: joke, fact, rps."""
    query = (inline_query.query or "").strip().lower()

    if not query:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="ℹ️ Inline-команды",
                description="joke, fact, rps",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "🤖 <b>Inline-команды бота:</b>\n"
                        "• joke — случайная шутка\n"
                        "• fact — случайный факт\n"
                        "• rps — камень-ножницы-бумага"
                    )
                ),
            )
        ]
        await inline_query.answer(results, cache_time=300, is_personal=False)
        return

    if query == "joke":
        await _fill_cache()
        joke = random.choice(_jokes_cache)
        # Refresh cache in background
        try:
            new_joke = await get_random_joke()
            _jokes_cache.append(new_joke)
            if len(_jokes_cache) > 10:
                _jokes_cache.pop(0)
        except Exception:
            pass
        results = [
            InlineQueryResultArticle(
                id="joke",
                title="😂 Шутка",
                description=joke[:100],
                input_message_content=InputTextMessageContent(
                    message_text=f"😂 <b>Шутка:</b>\n\n{joke}"
                ),
            )
        ]
        await inline_query.answer(results, cache_time=60, is_personal=True)
        return

    if query == "fact":
        await _fill_cache()
        fact = random.choice(_facts_cache)
        try:
            new_fact = await get_random_fact()
            _facts_cache.append(new_fact)
            if len(_facts_cache) > 10:
                _facts_cache.pop(0)
        except Exception:
            pass
        results = [
            InlineQueryResultArticle(
                id="fact",
                title="🧠 Факт",
                description=fact[:100],
                input_message_content=InputTextMessageContent(
                    message_text=f"🧠 <b>Интересный факт:</b>\n\n{fact}"
                ),
            )
        ]
        await inline_query.answer(results, cache_time=60, is_personal=True)
        return

    if query.startswith("rps"):
        parts = query.split()
        if len(parts) < 2 or parts[1] not in _RPS_CHOICES:
            results = [
                InlineQueryResultArticle(
                    id="rps_help",
                    title="🎮 Камень-ножницы-бумага",
                    description="rps rock/paper/scissors",
                    input_message_content=InputTextMessageContent(
                        message_text="🎮 Напиши: <code>inline rps rock</code>, <code>rps paper</code> или <code>rps scissors</code>"
                    ),
                )
            ]
            await inline_query.answer(results, cache_time=10, is_personal=True)
            return

        user_choice = parts[1]
        bot_choice = random.choice(list(_RPS_CHOICES.keys()))
        result_text = "Ничья! 🤝" if user_choice == bot_choice else _RPS_RESULT.get((user_choice, bot_choice), "?")
        text = (
            f"🎮 <b>Камень-ножницы-бумага:</b>\n\n"
            f"Ты: {_RPS_CHOICES[user_choice]} | Бот: {_RPS_CHOICES[bot_choice]}\n\n"
            f"<b>{result_text}</b>"
        )
        results = [
            InlineQueryResultArticle(
                id="rps_result",
                title=f"🎮 {result_text}",
                description=f"{_RPS_CHOICES[user_choice]} vs {_RPS_CHOICES[bot_choice]}",
                input_message_content=InputTextMessageContent(message_text=text),
            )
        ]
        await inline_query.answer(results, cache_time=5, is_personal=True)
        return

    await inline_query.answer([], cache_time=30, is_personal=False)
