import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActionLog, BannedSticker, Chat, ChatMember, GameStats, MessageLog, Note, Reputation, User, Warning


# ── User ──────────────────────────────────────────────────────────────────────

async def get_or_create_user(
    session: AsyncSession, telegram_id: int, **kwargs
) -> User:
    """Get existing user or create a new one."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(telegram_id=telegram_id, **kwargs)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update fields if provided
        changed = False
        for key, value in kwargs.items():
            if hasattr(user, key) and getattr(user, key) != value:
                setattr(user, key, value)
                changed = True
        if changed:
            await session.commit()

    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── Chat ──────────────────────────────────────────────────────────────────────

async def get_or_create_chat(
    session: AsyncSession, telegram_id: int, title: Optional[str] = None, chat_type: str = "private"
) -> Chat:
    stmt = select(Chat).where(Chat.telegram_id == telegram_id)
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()

    if chat is None:
        default_settings = {
            "antispam_enabled": True,
            "moderation_enabled": True,
            "captcha_enabled": True,
            "raid_mode_enabled": True,
            "bad_words": [],
            "filter_links": False,
            "filter_media": False,
            "nsfw_filter_enabled": True,
            "antiforward_enabled": False,
            "antispam_contacts": False,
            "welcome_message": "Добро пожаловать!",
        }
        chat = Chat(
            telegram_id=telegram_id,
            title=title,
            type=chat_type,
            settings=default_settings,
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    else:
        changed = False
        if title and chat.title != title:
            chat.title = title
            changed = True
        if chat_type and chat.type != chat_type:
            chat.type = chat_type
            changed = True
        if not chat.settings:
            chat.settings = {
                "antispam_enabled": True,
                "moderation_enabled": True,
                "captcha_enabled": True,
                "raid_mode_enabled": True,
                "bad_words": [],
                "filter_links": False,
                "filter_media": False,
                "welcome_message": "Добро пожаловать!",
            }
            changed = True
        if changed:
            await session.commit()

    return chat


async def update_chat_settings(
    session: AsyncSession, chat_id: int, settings_dict: dict
) -> Optional[Chat]:
    chat = await session.get(Chat, chat_id)
    if chat is None:
        return None
    chat.settings = {**(chat.settings or {}), **settings_dict}
    await session.commit()
    return chat


# ── Chat Member ───────────────────────────────────────────────────────────────

async def get_chat_member(
    session: AsyncSession, chat_id: int, user_id: int
) -> Optional[ChatMember]:
    stmt = select(ChatMember).where(
        ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_chat_member(
    session: AsyncSession, chat_id: int, user_id: int
) -> ChatMember:
    member = ChatMember(chat_id=chat_id, user_id=user_id)
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def increment_warnings(session: AsyncSession, chat_id: int, user_id: int) -> int:
    member = await get_chat_member(session, chat_id, user_id)
    if member is None:
        member = await add_chat_member(session, chat_id, user_id)
    member.warnings_count += 1
    await session.commit()
    return member.warnings_count


async def reset_warnings(session: AsyncSession, chat_id: int, user_id: int) -> None:
    member = await get_chat_member(session, chat_id, user_id)
    if member:
        member.warnings_count = 0
        await session.commit()


async def mute_member(
    session: AsyncSession, chat_id: int, user_id: int, duration: int
) -> None:
    member = await get_chat_member(session, chat_id, user_id)
    if member is None:
        member = await add_chat_member(session, chat_id, user_id)
    member.is_muted = True
    member.muted_until = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    await session.commit()


async def unmute_member(session: AsyncSession, chat_id: int, user_id: int) -> None:
    member = await get_chat_member(session, chat_id, user_id)
    if member:
        member.is_muted = False
        member.muted_until = None
        await session.commit()


# ── Warnings ──────────────────────────────────────────────────────────────────

async def add_warning(
    session: AsyncSession, chat_id: int, user_id: int, admin_id: int, reason: Optional[str] = None
) -> Warning:
    warn = Warning(chat_id=chat_id, user_id=user_id, admin_id=admin_id, reason=reason)
    session.add(warn)
    await session.commit()
    await session.refresh(warn)
    return warn


async def get_user_warnings(
    session: AsyncSession, chat_id: int, user_id: int
) -> list[Warning]:
    stmt = (
        select(Warning)
        .where(Warning.chat_id == chat_id, Warning.user_id == user_id)
        .order_by(Warning.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Notes ─────────────────────────────────────────────────────────────────────

async def add_note(
    session: AsyncSession, chat_id: int, user_id: int, admin_id: int, text: str
) -> Note:
    note = Note(chat_id=chat_id, user_id=user_id, admin_id=admin_id, text=text)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


async def get_user_notes(
    session: AsyncSession, chat_id: int, user_id: int
) -> list[Note]:
    from sqlalchemy import select

    stmt = (
        select(Note)
        .where(Note.chat_id == chat_id, Note.user_id == user_id)
        .order_by(Note.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_note(session: AsyncSession, note_id: int) -> bool:
    note = await session.get(Note, note_id)
    if note is None:
        return False
    await session.delete(note)
    await session.commit()
    return True


# ── Reputation ────────────────────────────────────────────────────────────────

async def give_reputation(
    session: AsyncSession, chat_id: int, user_id: int, given_by: int
) -> int:
    """Add a reputation point. Returns total reputation for user in chat."""
    rep = Reputation(chat_id=chat_id, user_id=user_id, given_by=given_by)
    session.add(rep)
    await session.commit()

    from sqlalchemy import select, func
    stmt = select(func.count(Reputation.id)).where(
        Reputation.chat_id == chat_id, Reputation.user_id == user_id
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_reputation(
    session: AsyncSession, chat_id: int, user_id: int
) -> int:
    """Get total reputation for a user in a chat."""
    from sqlalchemy import select, func
    stmt = select(func.count(Reputation.id)).where(
        Reputation.chat_id == chat_id, Reputation.user_id == user_id
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_top_reputation(
    session: AsyncSession, chat_id: int, limit: int = 10
) -> list[tuple[int, int]]:
    """Get top users by reputation. Returns list of (user_id, count)."""
    from sqlalchemy import select, func
    stmt = (
        select(Reputation.user_id, func.count(Reputation.id).label("rep"))
        .where(Reputation.chat_id == chat_id)
        .group_by(Reputation.user_id)
        .order_by(func.count(Reputation.id).desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.all())


# ── Game Stats ────────────────────────────────────────────────────────────────

async def update_game_stats(
    session: AsyncSession,
    user_id: int,
    game_type: str,
    outcome: str,  # 'win', 'loss', 'draw'
    chat_id: Optional[int] = None,
) -> GameStats:
    stmt = select(GameStats).where(
        GameStats.user_id == user_id,
        GameStats.game_type == game_type,
    )
    result = await session.execute(stmt)
    stats = result.scalar_one_or_none()

    if stats is None:
        stats = GameStats(
            user_id=user_id,
            chat_id=chat_id,
            game_type=game_type,
            wins=0,
            losses=0,
            draws=0,
        )
        session.add(stats)

    # Ensure values are not None (for old records)
    stats.wins = stats.wins if stats.wins is not None else 0
    stats.losses = stats.losses if stats.losses is not None else 0
    stats.draws = stats.draws if stats.draws is not None else 0

    if outcome == "win":
        stats.wins += 1
    elif outcome == "loss":
        stats.losses += 1
    elif outcome == "draw":
        stats.draws += 1

    await session.commit()
    await session.refresh(stats)
    return stats


async def get_top_players(
    session: AsyncSession, game_type: Optional[str] = None, limit: int = 10
) -> list[tuple[GameStats, User]]:
    stmt = select(GameStats, User).join(User).order_by(
        (GameStats.wins - GameStats.losses).desc()
    )
    if game_type:
        stmt = stmt.where(GameStats.game_type == game_type)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.all())


# ── Logging ───────────────────────────────────────────────────────────────────

async def log_action(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    action_type: str,
    admin_id: Optional[int] = None,
    details: Optional[str] = None,
) -> ActionLog:
    log = ActionLog(
        chat_id=chat_id,
        user_id=user_id,
        admin_id=admin_id,
        action_type=action_type,
        details=details,
    )
    session.add(log)
    await session.commit()
    return log


async def log_message(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    message_id: int,
    text: Optional[str] = None,
) -> MessageLog:
    msg_log = MessageLog(
        chat_id=chat_id,
        user_id=user_id,
        message_id=message_id,
        text=text,
    )
    session.add(msg_log)
    await session.commit()
    return msg_log


async def get_recent_joins(
    session: AsyncSession, chat_id: int, seconds: int = 30
) -> int:
    """Count how many users joined in the last N seconds (for raid detection)."""
    cutoff = datetime.datetime.now() - datetime.timedelta(seconds=seconds)
    stmt = (
        select(func.count(ActionLog.id))
        .where(
            ActionLog.chat_id == chat_id,
            ActionLog.action_type == "joined",
            ActionLog.created_at >= cutoff,
        )
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


# ── Banned Stickers ──────────────────────────────────────────────────────────

async def ban_sticker(
    session: AsyncSession, chat_id: int, file_unique_id: str, emoji: Optional[str], added_by: int
) -> BannedSticker:
    bs = BannedSticker(chat_id=chat_id, file_unique_id=file_unique_id, emoji=emoji, added_by=added_by)
    session.add(bs)
    await session.commit()
    await session.refresh(bs)
    return bs


async def is_sticker_banned(session: AsyncSession, chat_id: int, file_unique_id: str) -> bool:
    stmt = select(BannedSticker).where(
        BannedSticker.chat_id == chat_id,
        BannedSticker.file_unique_id == file_unique_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def unban_sticker(session: AsyncSession, chat_id: int, file_unique_id: str) -> bool:
    stmt = select(BannedSticker).where(
        BannedSticker.chat_id == chat_id,
        BannedSticker.file_unique_id == file_unique_id,
    )
    result = await session.execute(stmt)
    bs = result.scalar_one_or_none()
    if bs is None:
        return False
    await session.delete(bs)
    await session.commit()
    return True


# ── Chat Admins (bot-level) ─────────────────────────────────────────────────────

async def add_chat_admin(
    session: AsyncSession, chat_id: int, user_id: int, added_by: int, rank: int = 3
) -> None:
    """Add a bot-level admin to a chat. Rank: 1=junior, 2=admin, 3=head."""
    from db.models import ChatAdmin
    stmt = select(ChatAdmin).where(
        ChatAdmin.chat_id == chat_id, ChatAdmin.user_id == user_id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        # Update rank if already an admin
        existing.rank = rank
        await session.commit()
        return
    admin = ChatAdmin(chat_id=chat_id, user_id=user_id, rank=rank, added_by=added_by)
    session.add(admin)
    await session.commit()


async def remove_chat_admin(
    session: AsyncSession, chat_id: int, user_id: int
) -> bool:
    """Remove a bot-level admin from a chat."""
    from db.models import ChatAdmin
    stmt = select(ChatAdmin).where(
        ChatAdmin.chat_id == chat_id, ChatAdmin.user_id == user_id
    )
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    if admin is None:
        return False
    await session.delete(admin)
    await session.commit()
    return True


async def is_chat_admin_db(session: AsyncSession, chat_id: int, user_id: int) -> bool:
    """Check if user is a bot-level admin in this chat (any rank)."""
    from db.models import ChatAdmin
    stmt = select(ChatAdmin).where(
        ChatAdmin.chat_id == chat_id, ChatAdmin.user_id == user_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_chat_admin_rank(session: AsyncSession, chat_id: int, user_id: int) -> Optional[int]:
    """Get the bot admin rank for a user (1, 2, 3) or None if not a bot admin."""
    from db.models import ChatAdmin
    stmt = select(ChatAdmin).where(
        ChatAdmin.chat_id == chat_id, ChatAdmin.user_id == user_id
    )
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()
    return admin.rank if admin else None


async def list_chat_admins(session: AsyncSession, chat_id: int) -> list:
    """List all bot-level admins in a chat. Returns list of (User, rank)."""
    from db.models import ChatAdmin, User
    stmt = (
        select(User, ChatAdmin.rank)
        .join(ChatAdmin, ChatAdmin.user_id == User.id)
        .where(ChatAdmin.chat_id == chat_id)
        .order_by(ChatAdmin.rank.desc())
    )
    result = await session.execute(stmt)
    return list(result.all())


async def list_banned_stickers(session: AsyncSession, chat_id: int) -> list[BannedSticker]:
    stmt = (
        select(BannedSticker)
        .where(BannedSticker.chat_id == chat_id)
        .order_by(BannedSticker.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Scheduled Posts ────────────────────────────────────────────────────────

async def add_scheduled_post(
    session: AsyncSession,
    chat_telegram_id: int,
    text: str,
    interval_hours: int,
    created_by: int,
    photo_file_id: Optional[str] = None,
) -> "ScheduledPost":
    from db.models import ScheduledPost
    post = ScheduledPost(
        chat_telegram_id=chat_telegram_id,
        text=text,
        photo_file_id=photo_file_id,
        interval_hours=interval_hours,
        created_by=created_by,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def get_scheduled_posts(session: AsyncSession, chat_telegram_id: int) -> list:
    from db.models import ScheduledPost
    stmt = (
        select(ScheduledPost)
        .where(
            ScheduledPost.chat_telegram_id == chat_telegram_id,
            ScheduledPost.is_active == True,
        )
        .order_by(ScheduledPost.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_due_posts(session: AsyncSession) -> list:
    """Get all posts that are due to be sent."""
    from db.models import ScheduledPost
    now = datetime.datetime.now()
    stmt = select(ScheduledPost).where(ScheduledPost.is_active == True)
    result = await session.execute(stmt)
    all_posts = list(result.scalars().all())
    due = []
    for post in all_posts:
        if post.last_sent_at is None:
            due.append(post)
        else:
            elapsed = (now - post.last_sent_at).total_seconds()
            if elapsed >= post.interval_hours * 3600:
                due.append(post)
    return due


async def update_post_last_sent(session: AsyncSession, post_id: int) -> None:
    from db.models import ScheduledPost
    post = await session.get(ScheduledPost, post_id)
    if post:
        post.last_sent_at = datetime.datetime.now()
        await session.commit()


async def delete_scheduled_post(session: AsyncSession, post_id: int) -> bool:
    from db.models import ScheduledPost
    post = await session.get(ScheduledPost, post_id)
    if post is None:
        return False
    post.is_active = False
    await session.commit()
    return True
