import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from db.base import async_session_factory
from db.queries import (
    accept_marriage,
    divorce_marriage,
    get_marriage,
    get_or_create_user,
    get_pending_proposal,
    get_user_marriages,
    propose_marriage,
)
from filters.chat_type import IsReplyTo
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "relationships"

# Cooldown: (user_id, partner_id) -> timestamp for daily bonus
_daily_bonus_cooldown: dict[tuple[int, int], float] = {}
_DAILY_BONUS_COOLDOWN: float = 86400  # 24 hours
# Reputation bonus per day for being married
_DAILY_REP_BONUS_REPUTE: int = 1


@router.message(Command("marry"), IsReplyTo())
async def cmd_marry(message: Message) -> None:
    """Send marriage proposal. Usage: reply to user with /marry"""
    lang = await get_user_lang(message)

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.answer(t("marry_no_reply", lang))
        return

    target = message.reply_to_message.from_user

    if target.id == message.from_user.id:
        await message.answer(t("marry_self", lang))
        return

    if target.is_bot:
        await message.answer(t("marry_bot", lang))
        return

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        target_user = await get_or_create_user(session, telegram_id=target.id)

        # Check if already married
        existing = await get_marriage(session, user.telegram_id, target_user.telegram_id)
        if existing and existing["status"] == "married":
            await message.answer(t("marry_already", lang))
            return

        # Check if target has a pending proposal from this user
        pending = await get_pending_proposal(session, target_user.telegram_id)
        if pending and pending["proposer_id"] == user.telegram_id:
            await message.answer(t("marry_pending", lang))
            return

        # Check if target already has a pending proposal
        other_pending = await get_pending_proposal(session, target_user.telegram_id)
        if other_pending:
            await message.answer(t("marry_has_pending", lang))
            return

        # Check if target is already married
        target_marriages = await get_user_marriages(session, target_user.telegram_id)
        is_married = any(m["status"] == "married" for m in target_marriages)
        if is_married:
            await message.answer(t("marry_target_married", lang))
            return

        try:
            marriage = await propose_marriage(session, user.telegram_id, target_user.telegram_id)
        except ValueError as e:
            if str(e) == "already_married":
                await message.answer(t("marry_already", lang))
            else:
                await message.answer(t("marry_error", lang))
            return

    propose_text = (
        t("marry_propose", lang, name=message.from_user.first_name or "")
        if lang == "ru"
        else t("marry_propose_en", lang, name=message.from_user.first_name or "")
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💍 " + (t("marry_accept", lang) if lang == "ru" else "Accept"),
                    callback_data=f"marry_accept:{marriage.id}",
                ),
                InlineKeyboardButton(
                    text="❌ " + (t("marry_reject", lang) if lang == "ru" else "Reject"),
                    callback_data=f"marry_reject:{marriage.id}",
                ),
            ]
        ]
    )

    await message.answer(propose_text, reply_markup=kb)

    # Also DM the target user
    try:
        await message.bot.send_message(
            chat_id=target.id,
            text=(
                propose_text + "\n\n"
                + (t("marry_dm_accept", lang) if lang == "ru" else t("marry_dm_accept_en", lang))
            ),
            reply_markup=kb,
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("marry_accept:"))
async def on_marry_accept(callback: CallbackQuery) -> None:
    """Handle marriage proposal acceptance."""
    marriage_id_str = callback.data.removeprefix("marry_accept:")
    try:
        marriage_id = int(marriage_id_str)
    except ValueError:
        await callback.answer("Invalid", show_alert=True)
        return

    lang = await get_user_lang(callback)

    async with async_session_factory() as session:
        proposal = await get_pending_proposal(session, callback.from_user.id)
        if proposal is None:
            await callback.answer(
                t("marry_no_proposal", lang),
                show_alert=True,
            )
            return

        if proposal["id"] != marriage_id:
            await callback.answer(
                t("marry_wrong_proposal", lang),
                show_alert=True,
            )
            return

        try:
            await accept_marriage(session, marriage_id, callback.from_user.id)
        except ValueError as e:
            await callback.answer(str(e), show_alert=True)
            return

    partner_name_a = callback.from_user.first_name or f"User {callback.from_user.id}"
    proposer_text = t("marry_accepted", lang, name=partner_name_a)

    try:
        await callback.message.edit_text(proposer_text)
    except Exception:
        pass
    await callback.answer(t("marry_accepted_alert", lang), show_alert=True)

    # Notify proposer
    try:
        await callback.bot.send_message(
            chat_id=proposal["proposer_id"],
            text=t("marry_proposer_accepted", lang, name=partner_name_a),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("marry_reject:"))
async def on_marry_reject(callback: CallbackQuery) -> None:
    """Handle marriage proposal rejection."""
    marriage_id_str = callback.data.removeprefix("marry_reject:")
    try:
        marriage_id = int(marriage_id_str)
    except ValueError:
        await callback.answer("Invalid", show_alert=True)
        return

    lang = await get_user_lang(callback)

    async with async_session_factory() as session:
        proposal = await get_pending_proposal(session, callback.from_user.id)
        if proposal is None:
            await callback.answer(
                t("marry_no_proposal", lang),
                show_alert=True,
            )
            return

        if proposal["id"] != marriage_id:
            await callback.answer(
                t("marry_wrong_proposal", lang),
                show_alert=True,
            )
            return

        # Delete the pending proposal
        from db.models import Marriage
        m = await session.get(Marriage, marriage_id)
        if m:
            await session.delete(m)
            await session.commit()

    try:
        await callback.message.edit_text(t("marry_rejected", lang))
    except Exception:
        pass
    await callback.answer(t("marry_rejected_alert", lang), show_alert=True)

    # Notify proposer
    try:
        await callback.bot.send_message(
            chat_id=proposal["proposer_id"],
            text=t("marry_proposer_rejected", lang),
        )
    except Exception:
        pass


@router.message(Command("unmarry"))
async def cmd_unmarry(message: Message) -> None:
    """Initiate divorce. Usage: /unmarry"""
    lang = await get_user_lang(message)
    user_id = message.from_user.id

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=user_id)
        marriages = await get_user_marriages(session, user.telegram_id)
        active = [m for m in marriages if m["status"] == "married"]

    if not active:
        await message.answer(t("marry_not_married", lang))
        return

    partner_id = active[0]["partner_id"]

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=user_id)
        result = await divorce_marriage(session, user.telegram_id, partner_id)

    if result:
        await message.answer(t("marry_divorced", lang))
        try:
            await message.bot.send_message(
                chat_id=partner_id,
                text=t("marry_partner_divorced", lang, name=message.from_user.first_name or ""),
            )
        except Exception:
            pass
    else:
        await message.answer(t("marry_not_married", lang))


@router.message(Command("divorce"))
async def cmd_divorce(message: Message) -> None:
    """Alternative divorce command. Usage: /divorce"""
    await cmd_unmarry(message)


@router.message(Command("marriage"))
async def cmd_marriage(message: Message) -> None:
    """Show marriage status. Usage: /marriage or /status"""
    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        marriages = await get_user_marriages(session, user.telegram_id)

    active = [m for m in marriages if m["status"] == "married"]

    if not active:
        await message.answer(t("marry_single", lang))
        return

    m = active[0]
    partner_id = m["partner_id"]

    async with async_session_factory() as session:
        partner = await get_or_create_user(session, telegram_id=partner_id)

    partner_name = partner.first_name or f"User {partner_id}"
    married_date = (
        m["married_at"].strftime("%d.%m.%Y") if m["married_at"] else "Unknown"
    )

    lines = [
        f"💍 <b>{t('marry_status', lang)}</b>",
        f"👤 {t('marry_partner', lang)}: <b>{partner_name}</b>",
        f"📅 {t('marry_since', lang)}: {married_date}",
    ]

    # Daily bonus status
    key = (message.from_user.id, partner_id)
    from time import monotonic

    last = _daily_bonus_cooldown.get(key, 0)
    now = monotonic()
    remaining = max(0, _DAILY_BONUS_COOLDOWN - (now - last))

    if remaining > 0:
        hours = int(remaining // 3600)
        mins = int((remaining % 3600) // 60)
        lines.append(f"🎁 {t('marry_bonus_cd', lang)}: {hours}ч {mins}мин")
    else:
        lines.append(f"🎁 {t('marry_bonus_ready', lang)}")

    await message.answer("\n".join(lines))


@router.message(Command("gift"))
async def cmd_gift(message: Message) -> None:
    """Send reputation gift to partner. Usage: /gift @user or /gift"""
    lang = await get_user_lang(message)

    # Parse target
    target_id = None
    text = message.text.removeprefix("/gift").strip()
    if text:
        if text.startswith("@") and text[1:].isdigit():
            target_id = int(text[1:])
        else:
            await message.answer(t("marry_gift_usage", lang))
            return

    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        marriages = await get_user_marriages(session, user.telegram_id)
        active = [m for m in marriages if m["status"] == "married"]

    if not active:
        await message.answer(t("marry_not_married_gift", lang))
        return

    if target_id is None:
        # Gift to partner automatically
        target_id = active[0]["partner_id"]

    partner_id = active[0]["partner_id"]
    if target_id != partner_id:
        await message.answer(t("marry_not_partner", lang))
        return

    # Check cooldown (24h between gifts to same person)
    now = datetime.datetime.now().timestamp()
    cooldown_key = (message.from_user.id, target_id)
    last_gift = _daily_bonus_cooldown.get(cooldown_key, 0)
    if now - last_gift < _DAILY_BONUS_COOLDOWN:
        remaining = int(_DAILY_BONUS_COOLDOWN - (now - last_gift))
        hours = remaining // 3600
        mins = (remaining % 3600) // 60
        await message.answer(t("marry_gift_cd", lang, hours=hours, mins=mins))
        return

    _daily_bonus_cooldown[cooldown_key] = now

    # Award reputation to partner
    from db.queries import give_reputation
    async with async_session_factory() as session:
        partner = await get_or_create_user(session, telegram_id=target_id)
        total = await give_reputation(
            session,
            message.chat.id if message.chat else 0,
            partner.id,
            message.from_user.id,
        )

    await message.answer(
        t("marry_gift_sent", lang, name=partner.first_name or f"User {target_id}", total=total)
    )

    # Also notify partner
    try:
        await message.bot.send_message(
            chat_id=target_id,
            text=t("marry_gift_received", lang, name=message.from_user.first_name or ""),
        )
    except Exception:
        pass


@router.message(Command("familytop"))
async def cmd_familytop(message: Message) -> None:
    """Show top families by marriage count."""
    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        from db.models import Marriage
        from sqlalchemy import select

        married_stmt = select(Marriage).where(Marriage.status == "married")
        result = await session.execute(married_stmt)
        married = list(result.scalars().all())

    if not married:
        await message.answer(t("familytop_empty", lang))
        return

    # Count marriages per user
    counts: dict[int, int] = {}
    for m in married:
        counts[m.user1_id] = counts.get(m.user1_id, 0) + 1
        counts[m.user2_id] = counts.get(m.user2_id, 0) + 1

    sorted_users = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]

    lines = [f"💍 <b>{t('familytop_title', lang)}</b>"]
    for i, (uid, count) in enumerate(sorted_users, 1):
        async with async_session_factory() as session:
            user = await get_or_create_user(session, telegram_id=uid)
        name = user.first_name or f"User {uid}"
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        lines.append(f"{emoji} {name} — {count} брак(ов)")

    await message.answer("\n".join(lines))