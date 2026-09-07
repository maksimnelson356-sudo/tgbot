"""Tests for db/models.py and db/queries.py — async DB operations with in-memory SQLite."""

import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models import (
    ActionLog, BannedSticker, Chat, ChatAdmin, ChatMember,
    GameStats, Marriage, MessageLog, Note, Reminder, Reputation,
    ScheduledPost, User, Warning,
)
from db.queries import (
    get_or_create_user, get_or_create_chat, get_chat_member,
    add_chat_member, increment_warnings, reset_warnings,
    add_warning, get_user_warnings, mute_member, unmute_member,
    update_game_stats, log_action, log_message, get_recent_joins,
    ban_sticker, is_sticker_banned, unban_sticker,
    add_chat_admin, remove_chat_admin, is_chat_admin_db,
    get_chat_admin_rank, list_chat_admins,
    add_scheduled_post, get_scheduled_posts, deactivate_scheduled_post,
    update_post_last_sent, get_due_posts,
    add_note, get_user_notes, delete_note,
    give_reputation, get_reputation,
    propose_marriage, accept_marriage, divorce_marriage, get_marriage,
    level_for_xp, xp_for_level,
    add_xp,
)


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ── User tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_user(session):
    user = await get_or_create_user(session, telegram_id=12345, username="alice")
    assert user.telegram_id == 12345
    assert user.username == "alice"
    assert user.id is not None


@pytest.mark.asyncio
async def test_get_or_create_user_existing(session):
    u1 = await get_or_create_user(session, telegram_id=111, username="v1")
    u2 = await get_or_create_user(session, telegram_id=111, username="v2")
    assert u1.id == u2.id
    assert u2.username == "v2"


@pytest.mark.asyncio
async def test_user_defaults(session):
    user = await get_or_create_user(session, telegram_id=222)
    assert user.language == "ru"
    assert user.is_banned is False
    assert user.created_at is not None


# ── Chat tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_chat(session):
    chat = await get_or_create_chat(session, telegram_id=-100999, title="Test", chat_type="group")
    assert chat.telegram_id == -100999
    assert chat.title == "Test"
    assert chat.settings["antispam_enabled"] is True
    assert chat.settings["bad_words"] == []


@pytest.mark.asyncio
async def test_get_or_create_chat_existing(session):
    c1 = await get_or_create_chat(session, telegram_id=-1001, title="First")
    c2 = await get_or_create_chat(session, telegram_id=-1001, title="Second")
    assert c1.id == c2.id
    assert c2.title == "Second"


# ── ChatMember tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_chat_member(session):
    member = await add_chat_member(session, chat_id=1, user_id=10)
    assert member.chat_id == 1
    assert member.warnings_count == 0
    assert member.xp == 0


@pytest.mark.asyncio
async def test_add_chat_member_existing(session):
    m1 = await add_chat_member(session, chat_id=1, user_id=10)
    m2 = await add_chat_member(session, chat_id=1, user_id=10)
    assert m1.id == m2.id


@pytest.mark.asyncio
async def test_get_chat_member(session):
    await add_chat_member(session, chat_id=5, user_id=50)
    found = await get_chat_member(session, chat_id=5, user_id=50)
    assert found is not None
    missing = await get_chat_member(session, chat_id=5, user_id=999)
    assert missing is None


# ── Warning tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_increment_warnings(session):
    count = await increment_warnings(session, chat_id=1, user_id=10)
    assert count == 1
    count = await increment_warnings(session, chat_id=1, user_id=10)
    assert count == 2


@pytest.mark.asyncio
async def test_reset_warnings(session):
    await increment_warnings(session, chat_id=1, user_id=10)
    await increment_warnings(session, chat_id=1, user_id=10)
    await reset_warnings(session, chat_id=1, user_id=10)
    member = await get_chat_member(session, chat_id=1, user_id=10)
    assert member.warnings_count == 0


@pytest.mark.asyncio
async def test_add_warning(session):
    warn = await add_warning(session, chat_id=1, user_id=10, admin_id=5, reason="spam")
    assert warn.reason == "spam"
    warns = await get_user_warnings(session, chat_id=1, user_id=10)
    assert len(warns) == 1


# ── Mute tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mute_unmute(session):
    await mute_member(session, chat_id=1, user_id=10, duration=300)
    member = await get_chat_member(session, chat_id=1, user_id=10)
    assert member.is_muted is True
    assert member.muted_until is not None

    await unmute_member(session, chat_id=1, user_id=10)
    member = await get_chat_member(session, chat_id=1, user_id=10)
    assert member.is_muted is False
    assert member.muted_until is None


# ── GameStats tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_game_stats(session):
    stats = await update_game_stats(session, user_id=1, game_type="rps", outcome="win")
    assert stats.wins == 1
    assert stats.losses == 0

    stats = await update_game_stats(session, user_id=1, game_type="rps", outcome="loss")
    assert stats.wins == 1
    assert stats.losses == 1

    stats = await update_game_stats(session, user_id=1, game_type="rps", outcome="draw")
    assert stats.draws == 1


# ── ActionLog tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_log_action(session):
    log = await log_action(session, chat_id=-1001, user_id=111, action_type="warned", admin_id=555, details="spam")
    assert log.action_type == "warned"


@pytest.mark.asyncio
async def test_get_recent_joins(session):
    await log_action(session, chat_id=-1001, user_id=111, action_type="joined")
    await log_action(session, chat_id=-1001, user_id=222, action_type="joined")
    count = await get_recent_joins(session, chat_id=-1001, seconds=60)
    assert count == 2


@pytest.mark.asyncio
async def test_log_message(session):
    msg = await log_message(session, chat_id=-1001, user_id=111, message_id=999, text="hello")
    assert msg is not None


# ── BannedSticker tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ban_unban_sticker(session):
    bs = await ban_sticker(session, chat_id=1, file_unique_id="abc123", emoji="😀", added_by=5)
    assert bs.file_unique_id == "abc123"

    assert await is_sticker_banned(session, chat_id=1, file_unique_id="abc123") is True

    removed = await unban_sticker(session, chat_id=1, file_unique_id="abc123")
    assert removed is True
    assert await is_sticker_banned(session, chat_id=1, file_unique_id="abc123") is False


@pytest.mark.asyncio
async def test_ban_sticker_idempotent(session):
    bs1 = await ban_sticker(session, chat_id=1, file_unique_id="dup", emoji="🔴", added_by=5)
    bs2 = await ban_sticker(session, chat_id=1, file_unique_id="dup", emoji="🔴", added_by=5)
    assert bs1.file_unique_id == bs2.file_unique_id


# ── ChatAdmin tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_remove_chat_admin(session):
    await add_chat_admin(session, chat_id=1, user_id=10, added_by=5, rank=2)
    assert await is_chat_admin_db(session, chat_id=1, user_id=10) is True
    assert await get_chat_admin_rank(session, chat_id=1, user_id=10) == 2

    removed = await remove_chat_admin(session, chat_id=1, user_id=10)
    assert removed is True
    assert await is_chat_admin_db(session, chat_id=1, user_id=10) is False


@pytest.mark.asyncio
async def test_list_chat_admins(session):
    u1 = await get_or_create_user(session, telegram_id=10010)
    u2 = await get_or_create_user(session, telegram_id=10020)
    u3 = await get_or_create_user(session, telegram_id=10030)
    await add_chat_admin(session, chat_id=1, user_id=u1.id, added_by=u3.id, rank=1)
    await add_chat_admin(session, chat_id=1, user_id=u2.id, added_by=u3.id, rank=3)
    admins = await list_chat_admins(session, chat_id=1)
    assert len(admins) == 2


# ── ScheduledPost tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scheduled_post_crud(session):
    post = await add_scheduled_post(session, chat_telegram_id=-1001, text="Hello", interval_hours=24, created_by=5)
    assert post.text == "Hello"
    assert post.is_active is True

    posts = await get_scheduled_posts(session, chat_telegram_id=-1001)
    assert len(posts) == 1

    await deactivate_scheduled_post(session, post_id=post.id)
    posts = await get_scheduled_posts(session, chat_telegram_id=-1001)
    assert len(posts) == 0


@pytest.mark.asyncio
async def test_due_posts(session):
    post = await add_scheduled_post(session, chat_telegram_id=-1001, text="Due", interval_hours=1, created_by=5)
    # Set last_sent_at far in the past
    await update_post_last_sent(session, post_id=post.id)
    # Override last_sent_at to 2 hours ago
    from sqlalchemy import update
    from db.models import ScheduledPost
    two_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=2)
    await session.execute(update(ScheduledPost).where(ScheduledPost.id == post.id).values(last_sent_at=two_hours_ago))
    await session.commit()

    due = await get_due_posts(session)
    assert len(due) >= 1


# ── Note tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_note_crud(session):
    note = await add_note(session, chat_id=1, user_id=10, admin_id=5, text="remember this")
    notes = await get_user_notes(session, chat_id=1, user_id=10)
    assert len(notes) == 1

    deleted = await delete_note(session, note_id=note.id)
    assert deleted is True
    notes = await get_user_notes(session, chat_id=1, user_id=10)
    assert len(notes) == 0


# ── Reputation tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reputation(session):
    total = await give_reputation(session, chat_id=1, user_id=10, given_by=5)
    assert total == 1
    total = await give_reputation(session, chat_id=1, user_id=10, given_by=6)
    assert total == 2
    rep = await get_reputation(session, chat_id=1, user_id=10)
    assert rep == 2


# ── Marriage tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_marriage_flow(session):
    proposal = await propose_marriage(session, proposer_id=10, target_id=20)
    assert proposal.status == "pending"

    marriage = await accept_marriage(session, marriage_id=proposal.id, acceptor_id=20)
    assert marriage.status == "married"
    assert marriage.married_at is not None

    found = await get_marriage(session, user1_id=10, user2_id=20)
    assert found is not None
    assert found["status"] == "married"

    divorced = await divorce_marriage(session, user1_id=10, user2_id=20)
    assert divorced is True

    found = await get_marriage(session, user1_id=10, user2_id=20)
    assert found is None


@pytest.mark.asyncio
async def test_propose_already_married(session):
    p = await propose_marriage(session, proposer_id=10, target_id=20)
    await accept_marriage(session, marriage_id=p.id, acceptor_id=20)
    with pytest.raises(ValueError, match="already_married"):
        await propose_marriage(session, proposer_id=10, target_id=20)


# ── XP / Level tests ────────────────────────────────────────────────────────

def test_level_for_xp():
    assert level_for_xp(0) == 0
    assert level_for_xp(100) == 1
    assert level_for_xp(400) == 2
    assert level_for_xp(900) == 3


def test_xp_for_level():
    assert xp_for_level(0) == 0
    assert xp_for_level(1) == 100
    assert xp_for_level(2) == 400


@pytest.mark.asyncio
async def test_add_xp(session):
    await add_chat_member(session, chat_id=1, user_id=10)
    total, level = await add_xp(session, chat_id=1, user_id=10, amount=150)
    assert total == 150
    assert level == 1

    total, level = await add_xp(session, chat_id=1, user_id=10, amount=300)
    assert total == 450
    assert level == 2


@pytest.mark.asyncio
async def test_add_xp_no_member(session):
    total, level = await add_xp(session, chat_id=1, user_id=999, amount=100)
    assert total == 0
    assert level == 0


# ── FK cleanup migration test ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_message_log_insert_no_fk(session):
    """MessageLog uses raw Telegram IDs — verify insert works without FK errors."""
    log = await log_message(session, chat_id=-999999, user_id=888888, message_id=12345, text="test")
    assert log is not None
    assert log.chat_id == -999999


@pytest.mark.asyncio
async def test_action_log_insert_no_fk(session):
    """ActionLog uses raw Telegram IDs — verify insert works without FK errors."""
    log = await log_action(session, chat_id=-999999, user_id=888888, action_type="joined")
    assert log is not None
    assert log.chat_id == -999999
