import random

import aiohttp

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.external_api import get_random_fact, get_random_joke
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "fun"

# ── English content ──────────────────────────────────────────────────────────

_EN_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "What do you call a bear with no teeth? A gummy bear!",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why don't skeletons fight each other? They don't have the guts.",
    "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
    "Why did the scarecrow win an award? Because he was outstanding in his field!",
    "I'm reading a book on anti-gravity. It's impossible to put down!",
]

_EN_FACTS = [
    "A day on Venus is longer than a year on Venus.",
    "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still edible.",
    "Octopuses have three hearts.",
    "Bananas are berries, but strawberries aren't.",
    "The Eiffel Tower can be 15 cm taller during hot summer days.",
    "A group of flamingos is called a 'flamboyance'.",
    "The shortest war in history was between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after 38 minutes.",
    "Wombat poop is cube-shaped.",
    "Cows have best friends and get stressed when separated from them.",
    "A single cloud can weigh over a million pounds.",
]



# ── Russian content ──────────────────────────────────────────────────────────

_RU_JOKES = [
    "Встречаются два друга. Один говорит:\n— У меня жена — золото!\nВторой:\n— А моя — клад! Я её закопал и забыть не могу.",
    "Приходит мужик к врачу. Врач спрашивает:\n— На что жалуетесь?\n— Доктор, у меня всё болит!\n— А что именно?\n— Не знаю, я всё на всякий случай пожаловал.",
    "— Почему программисты путают Хэллоуин и Рождество?\n— Потому что Oct 31 == Dec 25.",
    "Сидит ёжик на пенёчке, жуёт соплю. Мимо проходит заяц:\n— Ёжик, что ты делаешь?\n— Да вот, соплю жую. Хочешь?\n— Нет, спасибо. \n— Правильно, я свою и сам схаваю.",
    "Штирлиц шёл по коридору и вдруг услышал шаги за спиной. Он резко обернулся и наступил себе на ногу.",
    "Вовочка спрашивает учительницу:\n— Марья Ивановна, а можно наказать человека за то, чего он не делал?\n— Нельзя, Вовочка!\n— Ура! Я сегодня домашнее задание не сделал!",
    "— Алло, это служба поддержки?\n— Да.\n— У меня компьютер не включается.\n— Вы подключили его к розетке?\n— ... А надо было?",
    "— Дорогой, я кажется потеряла кольцо!\n— Не переживай, я куплю тебе новое. А где ты его потеряла?\n— В ванной.\n— А что ты делала с кольцом в ванной?\n— Я мыла руки!",
    "Лежит человек на пляже, отдыхает. Подходит к нему другой:\n— Вы не подскажете, сколько времени?\n— Не знаю, я тут всего третий день.",
    "Работаю в IT-поддержке. Звонит женщина:\n— У меня не работает мышка!\n— Вы проверили, подключена ли она?\n— Да, я всё проверила!\n— А курсор на экране есть?\n— А кто это — курсор?!",
]

_RU_FACTS = [
    "День на Венере длиннее, чем год на Венере.",
    "Мёд никогда не портится. Археологи находили горшки с мёдом в древнеегипетских гробницах возрастом более 3000 лет, и он всё ещё съедобен.",
    "У осьминогов три сердца.",
    "Бананы — это ягоды, а клубника — нет.",
    "Эйфелева башня может стать выше на 15 см в жаркую погоду из-за теплового расширения.",
    "Группа фламинго называется «фламбуайянс» (flamboyance).",
    "Самая короткая война в истории длилась 38 минут — между Великобританией и Занзибаром в 1896 году.",
    "Какашки вомбатов имеют форму кубиков, чтобы не скатываться.",
    "У коров есть лучшие друзья, и они испытывают стресс при разлуке с ними.",
    "В Антарктиде есть реки и озёра подо льдом.",
    "Человеческий нос может различать более 1 триллиона запахов.",
    "Тигров больше в неволе, чем в дикой природе.",
    "Страусы — единственные птицы, у которых мочевой пузырь отделён от пищеварительной системы.",
    "Около 8% ДНК человека состоит из древних вирусов.",
]




@router.message(Command("joke"))
async def cmd_joke(message: Message) -> None:
    """Send a random joke."""
    lang = await get_user_lang(message)
    if lang == "ru":
        joke = random.choice(_RU_JOKES)
    else:
        try:
            joke = await get_random_joke()
        except Exception:
            joke = random.choice(_EN_JOKES)
    await message.answer(f"{t('joke_title', lang)}\n\n{joke}")


@router.message(Command("fact"))
async def cmd_fact(message: Message) -> None:
    """Send a random interesting fact."""
    lang = await get_user_lang(message)
    if lang == "ru":
        fact = random.choice(_RU_FACTS)
    else:
        try:
            fact = await get_random_fact()
        except Exception:
            fact = random.choice(_EN_FACTS)
    await message.answer(f"{t('fact_title', lang)}\n\n{fact}")


_HUG_GIF = "https://i.pinimg.com/originals/7b/73/4e/7b734ed8ced0bb4bd7964bb7f7335711.gif"


def _user_name(user) -> str:
    """Return display name for a user — prefer first_name."""
    if user.first_name:
        return f"<b>{user.first_name}</b>"
    if user.username:
        return f"@{user.username}"
    return "Unknown"


@router.message(Command("hug"))
@router.message(lambda msg: msg.text and msg.text.lower() in ("обнять", "обними", "обнимашки"))
async def cmd_hug(message: Message) -> None:
    """Hug someone! Usage: /hug (reply to msg) or /hug @username"""
    lang = await get_user_lang(message)
    hug_gif = _HUG_GIF
    sender = message.from_user

    # Find target: reply → @mention → fallback
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    elif message.text and " " in message.text:
        parts = message.text.split()
        for part in parts:
            if part.startswith("@"):
                username = part[1:].lower()
                # Search in chat members
                try:
                    async for member in message.chat.get_members():
                        if member.user.username and member.user.username.lower() == username:
                            target = member.user
                            break
                except Exception:
                    pass
                # Fallback: search admins
                if not target:
                    try:
                        admins = await message.chat.get_administrators()
                        for a in admins:
                            if a.user.username and a.user.username.lower() == username:
                                target = a.user
                                break
                    except Exception:
                        pass
                if not target:
                    text = f"🤗 <b>Обнимашки для @{username}!</b>" if lang != "ru" else f"🤗 <b>Обнимашки для @{username}!</b>"
                    await message.answer_animation(animation=hug_gif, caption=text)
                    return

    if target:
        s_name = _user_name(sender)
        if target.id == sender.id:
            text = "🤗 <b>Обнимашки!</b> Ты это заслужил!" if lang == "ru" else "🤗 <b>Self-hug!</b> You deserve it!"
        elif target.is_bot:
            text = "🤖 <b>Обнимашки бота!</b> Бип-буп 🤗" if lang == "ru" else "🤖 <b>Bot hug!</b> Beep boop 🤗"
        else:
            t_name = _user_name(target)
            text = f"🤗 {s_name} обнял(а) {t_name}!" if lang == "ru" else f"🤗 {s_name} hugged {t_name}!"
    else:
        text = "🤗 <b>Обнимашки!</b>" if lang == "ru" else "🤗 <b>Hug!</b>"

    try:
        await message.answer_animation(animation=hug_gif, caption=text)
    except Exception:
        await message.answer(text)


@router.message(Command("roll"))
async def cmd_roll(message: Message) -> None:
    """Roll a random number."""
    lang = await get_user_lang(message)
    number = random.randint(1, 100)
    await message.answer(t("roll_title", lang, number=number))
