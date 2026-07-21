import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_user, update_game_stats
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "games"

_games: dict[str, dict] = {}

_TRIVIA_QUESTIONS = [
    {"q": "What is the capital of France?", "options": ["London", "Paris", "Berlin", "Madrid"], "answer": 1},
    {"q": "How many continents are there on Earth?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"q": "What gas do plants absorb from the air?", "options": ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], "answer": 2},
    {"q": "What year did humans first walk on the Moon?", "options": ["1965", "1967", "1969", "1971"], "answer": 2},
    {"q": "Which planet is known as the Red Planet?", "options": ["Venus", "Jupiter", "Saturn", "Mars"], "answer": 3},
    {"q": "What is the largest mammal in the world?", "options": ["Elephant", "Blue whale", "Giraffe", "Hippopotamus"], "answer": 1},
    {"q": "In which country was sushi first made?", "options": ["China", "Korea", "Japan", "Thailand"], "answer": 2},
    {"q": "What is the chemical symbol for water?", "options": ["H2O", "CO2", "NaCl", "O2"], "answer": 0},
]

_TRIVIA_QUESTIONS_RU = [
    {"q": "Какая столица Франции?", "options": ["Лондон", "Париж", "Берлин", "Мадрид"], "answer": 1},
    {"q": "Сколько континентов на Земле?", "options": ["5", "6", "7", "8"], "answer": 2},
    {"q": "Какой газ поглощают растения из воздуха?", "options": ["Кислород", "Азот", "Углекислый газ", "Водород"], "answer": 2},
    {"q": "В каком году человек впервые вышел на Луну?", "options": ["1965", "1967", "1969", "1971"], "answer": 2},
    {"q": "Какая планета известна как Красная планета?", "options": ["Венера", "Юпитер", "Сатурн", "Марс"], "answer": 3},
    {"q": "Какое самое большое млекопитающее в мире?", "options": ["Слон", "Синий кит", "Жираф", "Бегемот"], "answer": 1},
    {"q": "В какой стране впервые начали делать суши?", "options": ["Китай", "Корея", "Япония", "Таиланд"], "answer": 2},
    {"q": "Как химический символ воды?", "options": ["H2O", "CO2", "NaCl", "O2"], "answer": 0},
]


@router.message(Command("dice"))
async def cmd_dice(message: Message) -> None:
    """Send a random dice result."""
    await message.answer_dice(emoji="🎲")
    async with async_session_factory() as session:
        await get_or_create_user(
            session, telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )


@router.message(Command("dart"))
async def cmd_dart(message: Message) -> None:
    await message.answer_dice(emoji="🎯")


@router.message(Command("bowling"))
async def cmd_bowling(message: Message) -> None:
    await message.answer_dice(emoji="🎳")


@router.message(Command("rps"))
async def cmd_rps(message: Message) -> None:
    lang = await get_user_lang(message)
    text = message.text.removeprefix("/rps").strip().lower()

    if text in ("rock", "камень", "🪨"):
        user_choice = "rock"
    elif text in ("paper", "бумага", "📄"):
        user_choice = "paper"
    elif text in ("scissors", "ножницы", "✂️"):
        user_choice = "scissors"
    else:
        await message.answer(t("rps_usage", lang))
        return

    bot_choice = random.choice(["rock", "paper", "scissors"])
    choices_emoji = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

    if user_choice == bot_choice:
        result_text = t("rps_draw", lang)
        outcome = "draw"
    elif (
        (user_choice == "rock" and bot_choice == "scissors")
        or (user_choice == "paper" and bot_choice == "rock")
        or (user_choice == "scissors" and bot_choice == "paper")
    ):
        result_text = t("rps_win", lang)
        outcome = "win"
    else:
        result_text = t("rps_loss", lang)
        outcome = "loss"

    async with async_session_factory() as session:
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id,
        )
        await update_game_stats(
            session, user.id, "rps", outcome, chat_id=message.chat.id,
        )

    await message.answer(
        f"🪨📄✂️ <b>Rock-Paper-Scissors!</b>\n\n"
        f"{t('rps_user', lang)}: {choices_emoji[user_choice]} {user_choice.capitalize()}\n"
        f"{t('rps_bot', lang)}: {choices_emoji[bot_choice]} {bot_choice.capitalize()}\n\n"
        f"<b>{result_text}</b>",
    )


@router.message(Command("guess"))
async def cmd_guess(message: Message) -> None:
    lang = await get_user_lang(message)
    text = message.text.removeprefix("/guess").strip()

    game_key = f"guess:{message.from_user.id}"

    if not text:
        number = random.randint(1, 10)
        _games[game_key] = {"number": number, "attempts": 0}
        await message.answer(t("guess_title", lang))
        return

    if not text.isdigit():
        await message.answer(t("guess_usage", lang))
        return

    guess = int(text)
    game = _games.get(game_key)

    if game is None:
        number = random.randint(1, 10)
        _games[game_key] = {"number": number, "attempts": 0}
        game = _games[game_key]

    game["attempts"] += 1
    number = game["number"]

    if guess == number:
        outcome = "win"
        text_result = t("guess_correct", lang, number=number, attempts=game["attempts"])
        del _games[game_key]

        async with async_session_factory() as session:
            user = await get_or_create_user(session, telegram_id=message.from_user.id)
            await update_game_stats(session, user.id, "guess", outcome, chat_id=message.chat.id)

        await message.answer(text_result)
    else:
        hint = t("guess_higher", lang) if guess < number else t("guess_lower", lang)
        text_result = t("guess_wrong", lang, hint=hint, attempts=game["attempts"])
        await message.answer(text_result)


@router.message(Command("trivia"))
async def cmd_trivia(message: Message) -> None:
    lang = await get_user_lang(message)
    text = message.text.removeprefix("/trivia").strip()
    game_key = f"trivia:{message.from_user.id}"

    if not text:
        questions = _TRIVIA_QUESTIONS_RU if lang == "ru" else _TRIVIA_QUESTIONS
        q = random.choice(questions)
        _games[game_key] = {"correct": q["answer"], "options": q["options"]}

        options_text = "\n".join(f"  {i + 1}. {opt}" for i, opt in enumerate(q["options"]))
        await message.answer(f"🧠 <b>Trivia!</b>\n\n{q['q']}\n\n{options_text}\n\n💡 /trivia <1-{len(q['options'])}>")
        return

    if not text.isdigit():
        await message.answer(t("trivia_usage", lang))
        return

    chosen = int(text) - 1
    game = _games.get(game_key)

    if game is None:
        await message.answer(t("trivia_no_active", lang))
        return

    if chosen < 0 or chosen >= len(game.get("options", [])):
        await message.answer(t("trivia_usage", lang))
        return

    outcome = "win" if chosen == game["correct"] else "loss"
    del _games[game_key]

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        await update_game_stats(session, user.id, "trivia", outcome, chat_id=message.chat.id)

    text_result = t("trivia_correct", lang) if outcome == "win" else t("trivia_wrong", lang)
    await message.answer(text_result)
