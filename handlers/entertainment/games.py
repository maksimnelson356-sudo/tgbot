import random

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from db.base import async_session_factory
from db.queries import get_or_create_user, update_game_stats
from keyboards.inline import guess_keyboard, rps_keyboard, trivia_keyboard
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
    """Start a Rock-Paper-Scissors game."""
    lang = await get_user_lang(message)
    await message.answer(t("rps_title", lang), reply_markup=rps_keyboard())


@router.callback_query(F.data.startswith("rps:"))
async def rps_callback(callback: CallbackQuery) -> None:
    if callback.message is None:
        return

    lang = await get_user_lang(callback)
    user_choice = callback.data.split(":")[1]
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
            session, telegram_id=callback.from_user.id,
        )
        await update_game_stats(
            session, user.id, "rps", outcome, chat_id=callback.message.chat.id,
        )

    await callback.message.edit_text(
        f"🪨📄✂️ <b>Rock-Paper-Scissors!</b>\n\n"
        f"{t('rps_user', lang)}: {choices_emoji[user_choice]} {user_choice.capitalize()}\n"
        f"{t('rps_bot', lang)}: {choices_emoji[bot_choice]} {bot_choice.capitalize()}\n\n"
        f"<b>{result_text}</b>",
    )
    await callback.answer()


@router.message(Command("guess"))
async def cmd_guess(message: Message) -> None:
    """Start a guess-the-number game."""
    lang = await get_user_lang(message)
    number = random.randint(1, 10)
    _games[f"guess:{message.from_user.id}"] = {"number": number, "attempts": 0}
    await message.answer(t("guess_title", lang), reply_markup=guess_keyboard())


@router.callback_query(F.data.startswith("guess:"))
async def guess_callback(callback: CallbackQuery) -> None:
    if callback.message is None:
        return

    lang = await get_user_lang(callback)
    guess = int(callback.data.split(":")[1])
    game = _games.get(f"guess:{callback.from_user.id}")

    if game is None:
        await callback.answer("No active game. Type /guess to start a new one!")
        return

    game["attempts"] += 1
    number = game["number"]

    if guess == number:
        outcome = "win"
        text = t("guess_correct", lang, number=number, attempts=game["attempts"])
        del _games[f"guess:{callback.from_user.id}"]

        async with async_session_factory() as session:
            user = await get_or_create_user(session, telegram_id=callback.from_user.id)
            await update_game_stats(session, user.id, "guess", outcome, chat_id=callback.message.chat.id)

        await callback.message.edit_text(text)
    else:
        hint = t("guess_higher", lang) if guess < number else t("guess_lower", lang)
        text = t("guess_wrong", lang, hint=hint, attempts=game["attempts"])
        await callback.answer(text)
        await callback.message.edit_reply_markup(reply_markup=guess_keyboard())

    await callback.answer()


@router.message(Command("trivia"))
async def cmd_trivia(message: Message) -> None:
    """Start a trivia game."""
    q = random.choice(_TRIVIA_QUESTIONS)
    _games[f"trivia:{message.from_user.id}"] = {"correct": q["answer"]}
    await message.answer(
        f"🧠 <b>Trivia!</b>\n\n{q['q']}",
        reply_markup=trivia_keyboard(q["options"]),
    )


@router.callback_query(F.data.startswith("trivia:"))
async def trivia_callback(callback: CallbackQuery) -> None:
    if callback.message is None:
        return

    lang = await get_user_lang(callback)
    chosen = int(callback.data.split(":")[1])
    game = _games.get(f"trivia:{callback.from_user.id}")

    if game is None:
        await callback.answer("No active trivia. Type /trivia to start!")
        return

    outcome = "win" if chosen == game["correct"] else "loss"
    del _games[f"trivia:{callback.from_user.id}"]

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=callback.from_user.id)
        await update_game_stats(session, user.id, "trivia", outcome, chat_id=callback.message.chat.id)

    text = t("trivia_correct", lang) if outcome == "win" else t("trivia_wrong", lang)
    await callback.message.edit_text(text)
    await callback.answer()
