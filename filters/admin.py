from aiogram.filters import Filter
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_chat_admin_rank


class IsAdmin(Filter):
    """Checks if the user is a Telegram admin OR any bot-level admin.

    Works only in group/supergroup chats.
    """

    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ("group", "supergroup"):
            return False
        if message.from_user is None:
            return False

        # 1. Check Telegram native admin
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return True

        # 2. Check bot-level admin in DB
        async with async_session_factory() as session:
            from db.queries import get_or_create_chat, get_or_create_user
            chat = await get_or_create_chat(session, telegram_id=message.chat.id)
            user = await get_or_create_user(session, telegram_id=message.from_user.id)
            return await get_chat_admin_rank(session, chat.id, user.id) is not None


class HasRank(Filter):
    """Checks if user is Telegram admin OR bot admin with rank >= min_rank.

    Rank 1 = младший, 2 = админ, 3 = главный.
    Telegram admins always pass any rank.
    """

    def __init__(self, min_rank: int = 1):
        self.min_rank = min_rank

    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in ("group", "supergroup"):
            return False
        if message.from_user is None:
            return False

        # Telegram admins always have full access
        member = await message.chat.get_member(message.from_user.id)
        if member.status in ("creator", "administrator"):
            return True

        # Check bot-level admin rank
        async with async_session_factory() as session:
            from db.queries import get_or_create_chat, get_or_create_user
            chat = await get_or_create_chat(session, telegram_id=message.chat.id)
            user = await get_or_create_user(session, telegram_id=message.from_user.id)
            rank = await get_chat_admin_rank(session, chat.id, user.id)
            return rank is not None and rank >= self.min_rank
