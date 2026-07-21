from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def rps_keyboard() -> InlineKeyboardMarkup:
    """Rock-paper-scissors choice keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🪨 Rock", callback_data="rps:rock")
    builder.button(text="📄 Paper", callback_data="rps:paper")
    builder.button(text="✂️ Scissors", callback_data="rps:scissors")
    builder.adjust(3)
    return builder.as_markup()


def trivia_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    """Trivia answer keyboard with 4 options."""
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"trivia:{i}")
    builder.adjust(2)
    return builder.as_markup()


def guess_keyboard() -> InlineKeyboardMarkup:
    """Number guess keyboard (1-10)."""
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"guess:{i}")
    builder.adjust(5)
    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Yes/No confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes", callback_data=f"{action}:yes")
    builder.button(text="❌ No", callback_data=f"{action}:no")
    builder.adjust(2)
    return builder.as_markup()


def back_keyboard(action: str = "back") -> InlineKeyboardMarkup:
    """Simple back button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Back", callback_data=action)
    return builder.as_markup()
