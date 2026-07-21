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
