from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from db.base import async_session_factory
from db.queries import get_or_create_user, get_top_players
from utils.i18n import t
from utils.lang_helper import get_user_lang

router = Router()
router.name = "leaderboard"


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    """Show leaderboard for all games."""
    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        results = await get_top_players(session, limit=10)

    if not results:
        await message.answer(t("leaderboard_empty", lang))
        return

    from db.models import GameStats
    from sqlalchemy import select

    lines = [t("leaderboard_title", lang)]

    # Build grouped by user
    user_data: dict[int, dict] = {}
    for stats, user in results:
        uid = user.id
        if uid not in user_data:
            user_data[uid] = {
                "name": user.first_name or f"User {user.telegram_id}",
                "games": [],
            }
        total = stats.wins + stats.losses + stats.draws
        win_rate = (stats.wins / total * 100) if total > 0 else 0
        gname = t(f"game_{stats.game_type}", lang, default=stats.game_type)
        user_data[uid]["games"].append(f"{gname}: {stats.wins}W / {stats.losses}L / {stats.draws}D ({win_rate:.0f}%)")

    for i, (uid, data) in enumerate(list(user_data.items())[:10], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
        lines.append(f"\n{emoji} <b>{data['name']}</b>")
        for g in data["games"]:
            lines.append(f"   {g}")

    # Add user's own stats if not in top
    async with async_session_factory() as session:
        user = await get_or_create_user(session, telegram_id=message.from_user.id)
        if user.id not in user_data:
            stmt = select(GameStats).where(GameStats.user_id == user.id)
            result = await session.execute(stmt)
            user_stats = list(result.scalars().all())
            if user_stats:
                lines.append(t("your_stats", lang))
                for s in user_stats:
                    gname = t(f"game_{s.game_type}", lang, default=s.game_type)
                    lines.append(f"   {gname}: {s.wins}W / {s.losses}L / {s.draws}D")

    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show personal game statistics."""
    lang = await get_user_lang(message)

    async with async_session_factory() as session:
        user = await get_or_create_user(
            session, telegram_id=message.from_user.id,
        )
        from db.models import GameStats
        from sqlalchemy import select
        stmt = select(GameStats).where(GameStats.user_id == user.id)
        result = await session.execute(stmt)
        all_stats = list(result.scalars().all())

    if not all_stats:
        await message.answer(t("stats_empty", lang))
        return

    lines = [t("stats_title", lang, name=message.from_user.first_name)]
    total_wins = total_losses = total_draws = 0
    for s in all_stats:
        gname = t(f"game_{s.game_type}", lang, default=s.game_type)
        lines.append(f"   {gname}: {s.wins}W / {s.losses}L / {s.draws}D")
        total_wins += s.wins
        total_losses += s.losses
        total_draws += s.draws

    total = total_wins + total_losses + total_draws
    if total > 0:
        win_rate = total_wins / total * 100
        lines.append(t("stats_overall", lang, total=total, win_rate=win_rate))

    await message.answer("\n".join(lines))
