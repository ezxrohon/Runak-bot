# ============================================================
# 🫧🦋 ʀuɴAk - Levels (XP progression)
# ============================================================
#
# Level curve: each level needs more XP than the last
# (Level 1→2 needs 100 XP, 2→3 needs 200 more, 3→4 needs 300 more, ...).
# XP itself is earned passively through economy/PvP actions
# (see grant_xp() calls in economy.py and pvp.py).
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db
from .common import resolve_target


def level_from_xp(xp: int):
    """Returns (level, xp_into_current_level, xp_needed_for_next_level)."""
    level = 1
    threshold = 0
    xp_for_next = 100
    while xp >= threshold + xp_for_next:
        threshold += xp_for_next
        level += 1
        xp_for_next = 100 * level
    return level, xp - threshold, xp_for_next


def progress_bar(current: int, total: int, length: int = 10) -> str:
    filled = int(length * current / total) if total else 0
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)


async def grant_xp(message: Message, user_id: int, amount: int):
    """Add XP to a user and reply with a level-up announcement if they crossed one.
    Safe to call even if amount is 0 or negative (no announcement then)."""
    if amount == 0:
        return await db.get_xp(user_id)

    old_xp = await db.get_xp(user_id)
    old_level, _, _ = level_from_xp(old_xp)
    new_xp = await db.add_xp(user_id, amount)
    new_level, _, _ = level_from_xp(new_xp)

    if new_level > old_level:
        try:
            await message.reply_text(
                f"🎉 **Level up!** You're now **Level {new_level}**!"
            )
        except Exception:
            pass

    return new_xp


def register_level_handlers(app: Client):

    @app.on_message(filters.command(["level", "lvl"]))
    async def level_cmd(client, message: Message):
        target = await resolve_target(client, message) or message.from_user
        await db.add_user(target.id, target.first_name)

        xp = await db.get_xp(target.id)
        level, into_level, needed = level_from_xp(xp)
        bar = progress_bar(into_level, needed)

        await message.reply_text(
            f"👤 **{target.first_name}**\n"
            f"🌟 **Level:** {level}\n"
            f"✨ **Total XP:** {xp}\n"
            f"📊 {bar} {into_level}/{needed} XP to Level {level + 1}"
        )

    @app.on_message(filters.command(["toplevel", "levels", "levelboard"]))
    async def toplevel_cmd(client, message: Message):
        top = await db.get_xp_leaderboard(10)
        if not top or all(e["xp"] == 0 for e in top):
            return await message.reply_text(
                "No one has earned XP yet — use /daily, /rob or /kill to start levelling up!"
            )

        lines = ["🌟 XP Leaderboard"]
        for i, entry in enumerate(top, start=1):
            if entry["xp"] == 0:
                break
            level, _, _ = level_from_xp(entry["xp"])
            lines.append(f"{i}. {entry['first_name']} — Level {level} ({entry['xp']} XP)")
        await message.reply_text("\n".join(lines))
