# ============================================================
# 🫧🦋 ʀuɴAk - Economy (Bubbles)
# ============================================================

import time
import random
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import Message
import db
from config import CURRENCY_NAME, CURRENCY_EMOJI, DAILY_REWARD, ROB_COOLDOWN_MIN, DAILY_ROB_LIMIT, DAILY_KILL_LIMIT
from .common import resolve_target, resolve_reply_target, format_protection_remaining
from .levels import grant_xp, level_from_xp
from .ui_formatter import card, ranked_list, notice, esc

HTML = ParseMode.HTML


def register_economy_handlers(app: Client):

    @app.on_message(filters.command(["balance", "bal"]))
    async def balance_cmd(client, message: Message):
        target = await resolve_target(client, message) or message.from_user
        await db.add_user(target.id, target.first_name)

        bal = await db.get_balance(target.id)
        rank = await db.get_rank(target.id)
        kills = await db.get_kills(target.id)
        status = await db.get_status(target.id)
        xp = await db.get_xp(target.id)
        level, _, _ = level_from_xp(xp)

        await message.reply_text(
            card(
                "WALLET",
                [
                    ("👤", "Name", target.first_name),
                    ("💰", "Balance", f"{bal:,} {CURRENCY_EMOJI}"),
                    ("🏆", "Global Rank", f"#{rank}"),
                    ("❤️", "Status", status),
                    ("🗡️", "Kills", kills),
                    ("🌟", "Level", f"{level} ({xp:,} XP)"),
                ],
                emoji="💎",
                theme="rainbow",
            ),
            parse_mode=HTML,
        )

    @app.on_message(filters.command("daily"))
    async def daily_cmd(client, message: Message):
        if message.chat.type != ChatType.PRIVATE:
            return await message.reply_text(
                notice("warn", f"/daily only works in DM — message me privately @{esc(client.me.username)} to claim it."),
                parse_mode=HTML,
            )

        user = message.from_user
        await db.add_user(user.id, user.first_name)

        last = await db.get_last_daily(user.id)
        now = time.time()
        elapsed = now - last
        cooldown = 24 * 60 * 60

        if elapsed < cooldown:
            remaining = cooldown - elapsed
            hrs = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            return await message.reply_text(notice("cooldown", f"Already claimed. Try again in {hrs}h {mins}m."), parse_mode=HTML)

        await db.add_balance(user.id, DAILY_REWARD)
        await db.set_last_daily(user.id)
        await message.reply_text(
            card(
                "DAILY REWARD",
                [("🎁", "Claimed", f"+{DAILY_REWARD:,} {CURRENCY_EMOJI} {CURRENCY_NAME}"), ("⚡", "Bonus", "+50 XP")],
                emoji="🎉",
                theme="gold",
                note="⏰ <i>Come back in 24 hours!</i>",
            ),
            parse_mode=HTML,
        )
        await grant_xp(message, user.id, 50)

    @app.on_message(filters.command("give"))
    async def give_cmd(client, message: Message):
        sender = message.from_user
        target = await resolve_target(client, message)

        if message.reply_to_message:
            amount = message.command[1] if len(message.command) > 1 else None
        else:
            amount = message.command[2] if len(message.command) > 2 else None

        if not target or not amount:
            return await message.reply_text(f"⚠️ Usage: /give <user> <amount> (or reply with /give <amount>)")

        try:
            amount = int(amount)
        except ValueError:
            return await message.reply_text("⚠️ Amount must be a number.")

        if amount <= 0:
            return await message.reply_text("⚠️ Amount must be positive.")

        if target.id == sender.id:
            return await message.reply_text("❌ You can't send Bubbles to yourself.")

        await db.add_user(sender.id, sender.first_name)
        await db.add_user(target.id, target.first_name)

        ok = await db.transfer_balance(sender.id, target.id, amount)
        if not ok:
            return await message.reply_text(f"❌ You don't have enough {CURRENCY_NAME}.")

        # Sender pays the full amount; a 10% fee is skimmed off what the
        # receiver actually gets (the fee simply leaves the economy).
        fee = amount // 10
        received = amount - fee
        if fee:
            await db.add_balance(target.id, -fee)

        await message.reply_text(
            card(
                "TRANSFER COMPLETE",
                [
                    ("📤", "From", sender.first_name),
                    ("📥", "To", target.first_name),
                    ("💸", "Sent", f"{amount:,} {CURRENCY_EMOJI}"),
                    ("🧾", "Fee (10%)", f"{fee:,} {CURRENCY_EMOJI}"),
                    ("✅", "Received", f"{received:,} {CURRENCY_EMOJI}"),
                ],
                emoji="💸",
                theme="forest",
            ),
            parse_mode=HTML,
        )

    @app.on_message(filters.command("rob"))
    async def rob_cmd(client, message: Message):
        robber = message.from_user
        # Reply-only - /rob @username with no reply is not accepted, so
        # people can't rob someone without actually engaging their message.
        victim = await resolve_reply_target(client, message)
        if not victim:
            return await message.reply_text("⚠️ Reply to the user you want to rob.")

        if victim.id == robber.id:
            return await message.reply_text("❌ You can't rob yourself.")

        await db.add_user(robber.id, robber.first_name)
        await db.add_user(victim.id, victim.first_name)

        daily_robs = await db.get_daily_robs(robber.id)
        if daily_robs >= DAILY_ROB_LIMIT:
            return await message.reply_text(
                f"🚫 You've hit today's rob limit ({DAILY_ROB_LIMIT}/{DAILY_ROB_LIMIT}). Try again tomorrow."
            )

        last_rob = await db.get_last_rob(robber.id)
        elapsed = time.time() - last_rob
        cooldown = ROB_COOLDOWN_MIN * 60
        if elapsed < cooldown:
            remaining = int((cooldown - elapsed) // 60) + 1
            return await message.reply_text(f"⏳ You're on cooldown. Try again in ~{remaining} min.")

        await db.set_last_rob(robber.id)
        await db.bump_daily_robs(robber.id)

        if await db.get_status(victim.id) == "dead":
            return await message.reply_text(f"💀 {victim.first_name} is dead. They can't be robbed until they revive.")

        remaining_protection = await db.get_protection_remaining(victim.id)
        if remaining_protection > 0:
            return await message.reply_text(
                f"🛡️ {victim.first_name} is already protected!\n"
                f"⏳ Remaining: {format_protection_remaining(remaining_protection)}"
            )

        if await db.has_item(victim.id, "shield"):
            await db.remove_item(victim.id, "shield")
            return await message.reply_text(
                f"🛡️ {victim.first_name}'s Shield blocked the robbery! (Shield consumed.)"
            )

        victim_balance = await db.get_balance(victim.id)
        if victim_balance < 20:
            return await message.reply_text(f"💸 {victim.first_name} is too broke to rob.")

        success = random.random() < 0.45  # 45% success rate
        if success:
            stolen = min(victim_balance, random.randint(10, max(11, victim_balance // 3)))
            await db.add_balance(victim.id, -stolen)
            await db.add_balance(robber.id, stolen)
            xp_gain = random.randint(10, 50)
            await message.reply_text(
                card(
                    "ROBBERY SUCCESS",
                    [
                        ("🦹", "Robber", robber.first_name),
                        ("🎯", "Victim", victim.first_name),
                        ("💰", "Stolen", f"{stolen:,} {CURRENCY_EMOJI}"),
                        ("⚡", "XP", f"+{xp_gain}"),
                    ],
                    emoji="🦹",
                    theme="forest",
                ),
                parse_mode=HTML,
            )
            await grant_xp(message, robber.id, xp_gain)
        else:
            fine = random.randint(10, 50)
            await db.add_balance(robber.id, -fine)
            await message.reply_text(
                card(
                    "BUSTED!",
                    [
                        ("🚓", "Caught", robber.first_name),
                        ("🎯", "Target", victim.first_name),
                        ("💸", "Fine", f"{fine:,} {CURRENCY_EMOJI}"),
                    ],
                    emoji="🚨",
                    theme="fire",
                ),
                parse_mode=HTML,
            )

    @app.on_message(filters.group & filters.command("claim"))
    async def claim_cmd(client, message: Message):
        user = message.from_user
        chat = message.chat

        if await db.has_claimed_group(chat.id):
            return await message.reply_text("❌ This group's reward has already been claimed.")

        try:
            count = await client.get_chat_members_count(chat.id)
        except Exception:
            return await message.reply_text("❌ Couldn't check this group's member count, try again shortly.")

        if count < 100:
            return await message.reply_text(f"⚠️ This group needs at least 100 members to claim (currently {count}).")

        if count >= 1000:
            reward = 30000
        elif count >= 500:
            reward = 20000
        else:
            reward = 10000

        await db.add_user(user.id, user.first_name)
        await db.set_claimed_group(chat.id, user.id)
        await db.add_balance(user.id, reward)
        await message.reply_text(
            card(
                "GROUP REWARD CLAIMED",
                [("🙋", "Claimed by", user.first_name), ("🎁", "Reward", f"+{reward:,} {CURRENCY_EMOJI} {CURRENCY_NAME}")],
                emoji="🎉",
                theme="gold",
            ),
            parse_mode=HTML,
        )

    @app.on_message(filters.command(["leaderboard", "gleaderboard"]))
    async def leaderboard_cmd(client, message: Message):
        top = await db.get_leaderboard(10)
        if not top:
            return await message.reply_text("No one has any Bubbles yet!")

        await message.reply_text(
            ranked_list(
                f"{CURRENCY_NAME.upper()} LEADERBOARD · GLOBAL",
                [(e.get("first_name", "Unknown"), f"{e.get('balance', 0):,} {CURRENCY_EMOJI}") for e in top],
            ),
            parse_mode=HTML,
        )

    @app.on_message(filters.group & filters.command("bleaderboard"))
    async def group_leaderboard_cmd(client, message: Message):
        top = await db.get_group_leaderboard(message.chat.id, 10)
        if not top:
            return await message.reply_text("No one here has any Bubbles yet — chat around a bit first!")

        await message.reply_text(
            ranked_list(
                f"{CURRENCY_NAME.upper()} LEADERBOARD · {esc(message.chat.title)}",
                [(e.get("first_name", "Unknown"), f"{e.get('balance', 0):,} {CURRENCY_EMOJI}") for e in top],
                theme="rainbow",
            ),
            parse_mode=HTML,
        )

    @app.on_message(filters.command("profile"))
    async def profile_cmd(client, message: Message):
        target = await resolve_target(client, message) or message.from_user
        await db.add_user(target.id, target.first_name)

        daily_kills = await db.get_daily_kills(target.id)
        daily_robs = await db.get_daily_robs(target.id)
        wallet = await db.get_balance(target.id)

        await message.reply_text(
            card(
                f"{esc(target.first_name)}'s PROFILE",
                [
                    ("☠️", "Daily Kills", f"{daily_kills}/{DAILY_KILL_LIMIT}"),
                    ("🔪", "Daily Robs", f"{daily_robs}/{DAILY_ROB_LIMIT}"),
                    ("💼", "Wallet", f"{wallet:,} {CURRENCY_EMOJI}"),
                ],
                emoji="👤",
                theme="royal",
            ),
            parse_mode=HTML,
        )
