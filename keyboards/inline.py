from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
