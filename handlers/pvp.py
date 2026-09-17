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
)
from .common import resolve_target, format_protection_remaining


def register_pvp_handlers(app: Client):

    @app.on_message(filters.command("kill"))
    async def kill_cmd(client, message: Message):
        killer = message.from_user
        victim = await resolve_target(client, message)
        if not victim:
            return await message.reply_text("⚠️ Reply to the user you want to kill.")

        if victim.id == killer.id:
            return await message.reply_text("❌ You can't kill yourself.")

        await db.add_user(killer.id, killer.first_name)
        await db.add_user(victim.id, victim.first_name)

        if await db.get_status(killer.id) == "dead":
            return await message.reply_text("💀 You're dead — use /revive before attacking anyone.")

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

        success = random.random() < KILL_SUCCESS_RATE
        if success:
            await db.set_status(victim.id, "dead")
            await db.add_kill(killer.id, 1)
            await db.set_protection(victim.id, PROTECTION_HOURS)
            await message.reply_text(
                f"⚠️ **You were killed!**\n"
                f"Killer: {killer.first_name}\n"
                f"You are now **dead**.",
            )
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

    @app.on_message(filters.command("topkill"))
    async def topkill_cmd(client, message: Message):
        top = await db.get_kill_leaderboard(10)
        if not top or all(e["kills"] == 0 for e in top):
            return await message.reply_text("No kills yet — be the first with /kill (reply to someone)!")

        lines = ["⚔️ Top Killers"]
        for i, entry in enumerate(top, start=1):
            if entry["kills"] == 0:
                break
            lines.append(f"{i}. {entry['first_name']} — {entry['kills']} kills")
        await message.reply_text("\n".join(lines))
