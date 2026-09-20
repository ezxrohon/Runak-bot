# ============================================================
# 🫧🦋 ʀuɴAk - PvP (kill / protection / revive)
# ============================================================

import time
import random
from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import (
    CURRENCY_NAME,
    CURRENCY_EMOJI,
    KILL_COOLDOWN_MIN,
    KILL_SUCCESS_RATE,
    PROTECTION_HOURS,
    REVIVE_COST,
    DAILY_KILL_LIMIT,
)
from .common import resolve_reply_target, format_protection_remaining
from .levels import grant_xp


def register_pvp_handlers(app: Client):

    @app.on_message(filters.command("kill"))
    async def kill_cmd(client, message: Message):
        killer = message.from_user
        # Reply-only - /kill @username with no reply is not accepted, so
        # people can't kill someone without actually engaging their message.
        victim = await resolve_reply_target(client, message)
        if not victim:
            return await message.reply_text("⚠️ Reply to the user you want to kill.")

        if victim.id == killer.id:
            return await message.reply_text("❌ You can't kill yourself.")

        await db.add_user(killer.id, killer.first_name)
        await db.add_user(victim.id, victim.first_name)

        if await db.get_status(killer.id) == "dead":
            return await message.reply_text("💀 You're dead — use /revive before attacking anyone.")

        daily_kills = await db.get_daily_kills(killer.id)
        if daily_kills >= DAILY_KILL_LIMIT:
            return await message.reply_text(
                f"🚫 You've hit today's kill limit ({DAILY_KILL_LIMIT}/{DAILY_KILL_LIMIT}). Try again tomorrow."
            )

        last_kill = await db.get_last_kill(killer.id)
        elapsed = time.time() - last_kill
        cooldown = KILL_COOLDOWN_MIN * 60
        if elapsed < cooldown:
            remaining = int((cooldown - elapsed) // 60) + 1
            return await message.reply_text(f"⏳ You're on cooldown. Try again in ~{remaining} min.")

        remaining_protection = await db.get_protection_remaining(victim.id)
        if remaining_protection > 0:
            return await message.reply_text(
                f"🛡️ {victim.first_name} is already protected!\n"
                f"⏳ Remaining: {format_protection_remaining(remaining_protection)}"
            )

        if await db.get_status(victim.id) == "dead":
            return await message.reply_text(f"💀 {victim.first_name} is already dead.")

        await db.set_last_kill(killer.id)
        await db.bump_daily_kills(killer.id)

        success = random.random() < KILL_SUCCESS_RATE
        if success:
            await db.set_status(victim.id, "dead")
            await db.add_kill(killer.id, 1)
            await db.set_protection(victim.id, PROTECTION_HOURS)
            xp_gain = random.randint(5, 15)
            await message.reply_text(
                f"⚠️ **You were killed!**\n"
                f"Killer: {killer.first_name} (+{xp_gain} XP)\n"
                f"You are now **dead**.",
            )
            await grant_xp(message, killer.id, xp_gain)
        else:
            fine = random.randint(20, 80)
            await db.add_balance(killer.id, -fine)
            await message.reply_text(
                f"🛡️ {victim.first_name} fought back! {killer.first_name} failed and paid a {fine} {CURRENCY_EMOJI} fine."
            )

    @app.on_message(filters.command("revive"))
    async def revive_cmd(client, message: Message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)

        if await db.get_status(user.id) != "dead":
            return await message.reply_text("❤️ You're already alive.")

        balance = await db.get_balance(user.id)
        if balance < REVIVE_COST:
            return await message.reply_text(
                f"❌ Reviving costs {REVIVE_COST} {CURRENCY_EMOJI}. You have {balance}."
            )

        await db.add_balance(user.id, -REVIVE_COST)
        await db.set_status(user.id, "alive")
        await db.clear_protection(user.id)
        await message.reply_text(f"💫 You paid {REVIVE_COST} {CURRENCY_EMOJI} and are back among the living!")

    @app.on_message(filters.command(["topkill", "gbkboard"]))
    async def topkill_cmd(client, message: Message):
        top = await db.get_kill_leaderboard(10)
        if not top or all(e["kills"] == 0 for e in top):
            return await message.reply_text("No kills yet — be the first with /kill (reply to someone)!")

        lines = ["⚔️ Top Killers (Global)"]
        for i, entry in enumerate(top, start=1):
            if entry["kills"] == 0:
                break
            lines.append(f"{i}. {entry['first_name']} — {entry['kills']} kills")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.group & filters.command("kleaderboard"))
    async def group_topkill_cmd(client, message: Message):
        top = await db.get_group_kill_leaderboard(message.chat.id, 10)
        if not top or all(e["kills"] == 0 for e in top):
            return await message.reply_text("No kills here yet — be the first with /kill (reply to someone)!")

        lines = [f"⚔️ Top Killers — {message.chat.title}"]
        for i, entry in enumerate(top, start=1):
            if entry["kills"] == 0:
                break
            lines.append(f"{i}. {entry['first_name']} — {entry['kills']} kills")
        await message.reply_text("\n".join(lines))
