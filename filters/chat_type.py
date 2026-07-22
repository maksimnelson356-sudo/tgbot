from aiogram.enums import ChatType
from aiogram.filters import Filter
from aiogram.types import Message


class IsGroup(Filter):
    """Filter for group chats only."""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


class IsPrivate(Filter):
    """Filter for private chats only."""

    async def __call__(self, message: Message) -> bool:
        return message.chat.type == ChatType.PRIVATE


class IsReplyToBot(Filter):
    """Filter: message is a reply to the bot's own message."""

    async def __call__(self, message: Message) -> bool:
        if not message.reply_to_message or not message.reply_to_message.from_user:
            return False
        return message.reply_to_message.from_user.id == message.bot.id
