import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActionLog, BannedSticker, Chat, ChatMember, GameStats, Marriage, MessageLog, Note, Reputation, User, Warning

if TYPE_CHECKING:  # runtime imports are lazy inside the functions that use them
    from db.models import Reminder, ScheduledPost


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
        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            await session.rollback()
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one()
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
            "captcha_enabled": False,
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
        try:
            await session.commit()
            await session.refresh(chat)
        except IntegrityError:
            await session.rollback()
            stmt = select(Chat).where(Chat.telegram_id == telegram_id)
            result = await session.execute(stmt)
            chat = result.scalar_one()
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
                "captcha_enabled": False,
                "raid_mode_enabled": True,
                "bad_words": [],
                "filter_links": False,
                "filter_media": False,
                "nsfw_filter_enabled": True,
                "antiforward_enabled": False,
                "antispam_contacts": False,
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


async def get_all_chat_ids(session: AsyncSession) -> list[int]:
    stmt = select(Chat.telegram_id)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


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
    existing = await get_chat_member(session, chat_id, user_id)
    if existing:
        return existing
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
    session: AsyncSession, chat_id: int, user_id: int,
    admin_id: Optional[int] = None, reason: Optional[str] = None
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


async def delete_note(session: AsyncSession, note_id: int, chat_id: Optional[int] = None) -> bool:
    stmt = select(Note).where(Note.id == note_id)
    if chat_id is not None:
        stmt = stmt.where(Note.chat_id == chat_id)
    note = (await session.execute(stmt)).scalar_one_or_none()
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


async def get_last_rep_given_at(
    session: AsyncSession, chat_id: int, target_user_id: int, giver_user_id: int
) -> Optional[datetime.datetime]:
    """Timestamp of the last rep the giver gave to this target in this chat."""
    stmt = (
        select(Reputation.created_at)
        .where(
            Reputation.chat_id == chat_id,
            Reputation.user_id == target_user_id,
            Reputation.given_by == giver_user_id,
        )
        .order_by(Reputation.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def count_rep_given_today(
    session: AsyncSession, chat_id: int, giver_user_id: int
) -> int:
    """How many rep points the giver has handed out in this chat today."""
    from sqlalchemy import select, func
    day_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.count(Reputation.id)).where(
        Reputation.chat_id == chat_id,
        Reputation.given_by == giver_user_id,
        Reputation.created_at >= day_start,
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
    """Get top users by reputation. Returns list of (telegram_id, count)."""
    from sqlalchemy import select, func
    stmt = (
        select(User.telegram_id, func.count(Reputation.id).label("rep"))
        .join(User, User.id == Reputation.user_id)
        .where(Reputation.chat_id == chat_id)
        .group_by(User.telegram_id)
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
    chat_telegram_id: Optional[int] = None,
) -> GameStats:
    # Resolve internal chats.id PK from the Telegram chat id
    chat_pk: Optional[int] = None
    if chat_telegram_id is not None:
        chat = await get_or_create_chat(session, telegram_id=chat_telegram_id)
        chat_pk = chat.id

    # Ensure row exists
    stmt = select(GameStats).where(
        GameStats.user_id == user_id,
        GameStats.game_type == game_type,
    )
    result = await session.execute(stmt)
    stats = result.scalar_one_or_none()

    if stats is None:
        stats = GameStats(
            user_id=user_id,
            chat_id=chat_pk,
            game_type=game_type,
            wins=0,
            losses=0,
            draws=0,
        )
        session.add(stats)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            result = await session.execute(stmt)
            stats = result.scalar_one()

    # Atomic increment
    from sqlalchemy import update
    col = GameStats.wins if outcome == "win" else GameStats.losses if outcome == "loss" else GameStats.draws
    await session.execute(
        update(GameStats)
        .where(GameStats.user_id == user_id, GameStats.game_type == game_type)
        .values(**{col.key: col + 1})
    )
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
    try:
        await session.commit()
        await session.refresh(bs)
        return bs
    except IntegrityError:
        await session.rollback()
        stmt = select(BannedSticker).where(
            BannedSticker.chat_id == chat_id,
            BannedSticker.file_unique_id == file_unique_id,
        )
        result = await session.execute(stmt)
        return result.scalars().first()


async def is_sticker_banned(session: AsyncSession, chat_id: int, file_unique_id: str) -> bool:
    stmt = select(BannedSticker).where(
        BannedSticker.chat_id == chat_id,
        BannedSticker.file_unique_id == file_unique_id,
    )
    result = await session.execute(stmt)
    return result.scalars().first() is not None


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


async def get_user_any_admin_rank(session: AsyncSession, telegram_id: int) -> bool:
    """Check if user is a bot-level admin in ANY chat."""
    from db.models import ChatAdmin
    stmt = select(ChatAdmin).join(User, ChatAdmin.user_id == User.id).where(
        User.telegram_id == telegram_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_user_admin_chats(session: AsyncSession, telegram_id: int) -> list:
    """Get all chats where user is a bot-level admin. Returns list of Chat objects."""
    from db.models import ChatAdmin
    stmt = (
        select(Chat)
        .join(ChatAdmin, ChatAdmin.chat_id == Chat.id)
        .join(User, ChatAdmin.user_id == User.id)
        .where(User.telegram_id == telegram_id, Chat.type.in_(("group", "supergroup")))
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


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
    media_type: Optional[str] = None,
) -> "ScheduledPost":
    from db.models import ScheduledPost
    post = ScheduledPost(
        chat_telegram_id=chat_telegram_id,
        text=text,
        photo_file_id=photo_file_id,
        media_type=media_type,
        interval_hours=interval_hours,
        created_by=created_by,
        # Seed so interval posts don't fire instantly after creation
        last_sent_at=datetime.datetime.now(),
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


async def deactivate_scheduled_post(session: AsyncSession, post_id: int) -> None:
    """Disable a post after repeated send failures."""
    from db.models import ScheduledPost
    post = await session.get(ScheduledPost, post_id)
    if post:
        post.is_active = False
        await session.commit()


async def delete_old_message_logs(session: AsyncSession, days: int = 30) -> int:
    """Retention job: delete message log rows older than N days. Returns count."""
    from db.models import MessageLog
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    from sqlalchemy import delete as sa_delete
    result = await session.execute(sa_delete(MessageLog).where(MessageLog.created_at < cutoff))
    await session.commit()
    return result.rowcount or 0


# ── XP / levels / daily bonus (G2) ────────────────────────────────────────────

def level_for_xp(xp: int) -> int:
    """Level thresholds: 100, 400, 900, 1600… → level = floor(sqrt(xp/100))."""
    if xp <= 0:
        return 0
    return int((xp // 100) ** 0.5)


def xp_for_level(level: int) -> int:
    return 100 * max(level, 0) ** 2


async def add_xp(
    session: AsyncSession, chat_id: int, user_id: int, amount: int
) -> tuple[int, int]:
    """Add XP to a chat member. Returns (new_total_xp, new_level)."""
    member = await get_chat_member(session, chat_id, user_id)
    if member is None:
        return 0, 0
    member.xp = (member.xp or 0) + amount
    await session.commit()
    return member.xp, level_for_xp(member.xp)


async def claim_daily(
    session: AsyncSession, chat_id: int, user_id: int
) -> tuple[bool, int, int]:
    """Claim the daily streak bonus.

    Returns (claimed, streak, xp_reward). Streak continues when claimed
    on consecutive calendar days, otherwise resets to 1.
    """
    import datetime as _dt

    member = await get_chat_member(session, chat_id, user_id)
    if member is None:
        return False, 0, 0

    now = _dt.datetime.now()
    last = member.last_daily_at
    consecutive = False

    if last is not None:
        elapsed = (now - last).total_seconds()
        if elapsed < 20 * 3600:  # less than ~a day — not yet
            return False, member.daily_streak or 0, 0
        consecutive = last.date() == (now - _dt.timedelta(days=1)).date()

    if consecutive:
        member.daily_streak = (member.daily_streak or 0) + 1
    else:
        member.daily_streak = 1

    member.last_daily_at = now
    streak = member.daily_streak
    reward = 50 + min(streak - 1, 6) * 25  # 50..200
    member.xp = (member.xp or 0) + reward
    await session.commit()
    return True, streak, reward


async def top_xp(session: AsyncSession, chat_id: int, limit: int = 10):
    """Top members by XP. Returns [(user_telegram_id, xp, level)]."""
    from sqlalchemy import select
    from db.models import ChatMember, User
    stmt = (
        select(User.telegram_id, ChatMember.xp)
        .join(User, User.id == ChatMember.user_id)
        .where(ChatMember.chat_id == chat_id)
        .order_by(ChatMember.xp.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [(tg, xp or 0, level_for_xp(xp or 0)) for tg, xp in result.all()]


async def count_invites(session: AsyncSession, chat_id: int, inviter_user_id: int) -> int:
    """How many current members this user has invited to the chat."""
    from sqlalchemy import select, func
    from db.models import ChatMember
    stmt = select(func.count(ChatMember.id)).where(
        ChatMember.chat_id == chat_id,
        ChatMember.invited_by == inviter_user_id,
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def set_invited_by(
    session: AsyncSession, chat_id: int, new_member_user_id: int, inviter_user_id: int
) -> None:
    """Attribute a join to an inviter (first write wins)."""
    from db.models import ChatMember
    member = await get_chat_member(session, chat_id, new_member_user_id)
    if member is not None and member.invited_by is None:
        member.invited_by = inviter_user_id
        await session.commit()


async def get_top_inviters(session: AsyncSession, chat_id: int, limit: int = 10):
    """Top inviters: [(inviter_user_id, invite_count)]."""
    from sqlalchemy import select, func
    from db.models import ChatMember
    stmt = (
        select(ChatMember.invited_by, func.count(ChatMember.id))
        .where(ChatMember.chat_id == chat_id, ChatMember.invited_by.isnot(None))
        .group_by(ChatMember.invited_by)
        .order_by(func.count(ChatMember.id).desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [(uid, cnt) for uid, cnt in result.all()]


async def set_referred_by(
    session: AsyncSession, new_user_pk: int, referrer_telegram_id: int
) -> bool:
    """Store the referrer for a user (once). Returns True if newly credited."""
    user = await session.get(User, new_user_pk)
    if user is None or user.referred_by is not None:
        return False
    referrer = (
        await session.execute(select(User).where(User.telegram_id == referrer_telegram_id))
    ).scalar_one_or_none()
    if referrer is None:
        return False  # referrer has never talked to the bot — ignore
    user.referred_by = referrer.id
    await session.commit()
    return True


async def get_referred_by(session: AsyncSession, user_pk: int) -> Optional[int]:
    """Internal users.id of this user's referrer, or None."""
    user = await session.get(User, user_pk)
    return user.referred_by if user else None


async def count_prior_joins(session: AsyncSession, telegram_chat_id: int, telegram_user_id: int) -> int:
    """How many times this user already joined this chat before now."""
    from db.models import ActionLog
    from sqlalchemy import select, func

    chat = await get_or_create_chat(session, telegram_id=telegram_chat_id)
    user = await get_or_create_user(session, telegram_id=telegram_user_id)
    stmt = select(func.count(ActionLog.id)).where(
        ActionLog.chat_id == chat.id,
        ActionLog.user_id == user.id,
        ActionLog.action_type == "joined",
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def delete_scheduled_post(
    session: AsyncSession, post_id: int, chat_telegram_id: Optional[int] = None
) -> bool:
    from db.models import ScheduledPost
    stmt = select(ScheduledPost).where(ScheduledPost.id == post_id)
    if chat_telegram_id is not None:
        stmt = stmt.where(ScheduledPost.chat_telegram_id == chat_telegram_id)
    post = (await session.execute(stmt)).scalar_one_or_none()
    if post is None:
        return False
    post.is_active = False
    await session.commit()
    return True


# ── Marriages ──────────────────────────────────────────────────────────

async def get_marriage(
    session: AsyncSession, user1_id: int, user2_id: int
) -> Optional[dict]:
    """Check if two users are married. Returns marriage record or None."""
    from db.models import Marriage
    stmt1 = select(Marriage).where(
        Marriage.user1_id == user1_id,
        Marriage.user2_id == user2_id,
        Marriage.status == "married",
    )
    stmt2 = select(Marriage).where(
        Marriage.user1_id == user2_id,
        Marriage.user2_id == user1_id,
        Marriage.status == "married",
    )
    for stmt in (stmt1, stmt2):
        result = await session.execute(stmt)
        marriage = result.scalar_one_or_none()
        if marriage:
            other_id = marriage.user2_id if marriage.user1_id == user1_id else marriage.user1_id
            return {
                "id": marriage.id,
                "partner_id": other_id,
                "status": marriage.status,
                "married_at": marriage.married_at,
                "proposer_id": marriage.proposer_id,
            }
    return None


async def get_pending_proposal(
    session: AsyncSession, user_id: int
) -> Optional[dict]:
    """Check if user has a pending marriage proposal."""
    from db.models import Marriage
    stmt = select(Marriage).where(
        Marriage.user2_id == user_id,
        Marriage.status == "pending",
    )
    result = await session.execute(stmt)
    proposal = result.scalar_one_or_none()
    if proposal:
        return {
            "id": proposal.id,
            "proposer_id": proposal.proposer_id,
            "created_at": proposal.created_at,
        }
    return None


async def get_user_marriages(
    session: AsyncSession, user_id: int
) -> list[dict]:
    """Get all marriages (including divorced) for a user."""
    from db.models import Marriage
    stmt = select(Marriage).where(
        (Marriage.user1_id == user_id) | (Marriage.user2_id == user_id),
    )
    result = await session.execute(stmt)
    marriages = list(result.scalars().all())
    out = []
    for m in marriages:
        other_id = m.user2_id if m.user1_id == user_id else m.user1_id
        out.append(
            {
                "id": m.id,
                "partner_id": other_id,
                "status": m.status,
                "married_at": m.married_at,
                "divorced_at": m.divorced_at,
                "proposer_id": m.proposer_id,
            }
        )
    return out


async def propose_marriage(
    session: AsyncSession, proposer_id: int, target_id: int
) -> Marriage:
    """Create a pending marriage proposal."""
    from db.models import Marriage
    existing = await get_marriage(session, proposer_id, target_id)
    if existing and existing["status"] == "married":
        raise ValueError("already_married")

    marriage = Marriage(
        user1_id=proposer_id,
        user2_id=target_id,
        status="pending",
        proposer_id=proposer_id,
    )
    session.add(marriage)
    await session.commit()
    await session.refresh(marriage)
    return marriage


async def accept_marriage(
    session: AsyncSession, marriage_id: int, acceptor_id: int
) -> Marriage:
    """Accept a pending marriage proposal."""
    from db.models import Marriage
    marriage = await session.get(Marriage, marriage_id)
    if marriage is None:
        raise ValueError("proposal_not_found")
    if marriage.status != "pending":
        raise ValueError("not_pending")
    if marriage.user2_id != acceptor_id:
        raise ValueError("not_target")

    marriage.status = "married"
    marriage.acceptor_id = acceptor_id
    marriage.married_at = datetime.datetime.now()
    await session.commit()
    await session.refresh(marriage)
    return marriage


async def divorce_marriage(
    session: AsyncSession, user1_id: int, user2_id: int
) -> bool:
    """Divorce two users."""
    from db.models import Marriage
    stmt1 = select(Marriage).where(
        Marriage.user1_id == user1_id,
        Marriage.user2_id == user2_id,
        Marriage.status == "married",
    )
    stmt2 = select(Marriage).where(
        Marriage.user1_id == user2_id,
        Marriage.user2_id == user1_id,
        Marriage.status == "married",
    )
    for stmt in (stmt1, stmt2):
        result = await session.execute(stmt)
        marriage = result.scalar_one_or_none()
        if marriage:
            marriage.status = "divorced"
            marriage.divorced_at = datetime.datetime.now()
            await session.commit()
            return True
    return False


# ── Reminders ────────────────────────────────────────────────────────────────

async def create_reminder(
    session: AsyncSession, user_id: int, chat_id: int, text: str, remind_at: datetime.datetime
) -> "Reminder":
    from db.models import Reminder
    r = Reminder(user_id=user_id, chat_id=chat_id, text=text, remind_at=remind_at)
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r


async def get_due_reminders(session: AsyncSession) -> list:
    from db.models import Reminder
    now = datetime.datetime.now()
    stmt = select(Reminder).where(
        Reminder.is_sent == False,
        Reminder.remind_at <= now,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_reminder_sent(session: AsyncSession, reminder_id: int) -> None:
    from db.models import Reminder
    r = await session.get(Reminder, reminder_id)
    if r:
        r.is_sent = True
        await session.commit()
