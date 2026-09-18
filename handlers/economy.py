# ============================================================
# 🫧🦋 ʀuɴAk - Economy (Bubbles)
# ============================================================

import time
import random
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message
import db
from config import CURRENCY_NAME, CURRENCY_EMOJI, DAILY_REWARD, ROB_COOLDOWN_MIN
from .common import resolve_target, format_protection_remaining
from .levels import grant_xp, level_from_xp


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
            f"👤 **Name:** {target.first_name}\n"
            f"💰 **Total Balance:** ${bal}\n"
            f"🏆 **Global Rank:** {rank}\n"
            f"❤️ **Status:** {status}\n"
            f"🗡️ **Kills:** {kills}\n"
            f"🌟 **Level:** {level} ({xp} XP)"
        )

    @app.on_message(filters.command("daily"))
    async def daily_cmd(client, message: Message):
        if message.chat.type != ChatType.PRIVATE:
            return await message.reply_text(
                f"⚠️ /daily only works in DM — message me privately @{client.me.username} to claim it."
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
            return await message.reply_text(f"⏳ Already claimed. Try again in {hrs}h {mins}m.")

        await db.add_balance(user.id, DAILY_REWARD)
        await db.set_last_daily(user.id)
        await message.reply_text(f"🎁 You claimed your daily {DAILY_REWARD} {CURRENCY_EMOJI} {CURRENCY_NAME}! (+50 XP)")
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
            f"✅ {sender.first_name} sent {amount} {CURRENCY_EMOJI} to {target.first_name}!\n"
            f"💸 10% fee applied — {target.first_name} received {received} {CURRENCY_EMOJI}."
        )

    @app.on_message(filters.command("rob"))
    async def rob_cmd(client, message: Message):
        robber = message.from_user
        victim = await resolve_target(client, message)
        if not victim:
            return await message.reply_text("⚠️ Reply to the user you want to rob.")

        if victim.id == robber.id:
            return await message.reply_text("❌ You can't rob yourself.")

        await db.add_user(robber.id, robber.first_name)
        await db.add_user(victim.id, victim.first_name)

        last_rob = await db.get_last_rob(robber.id)
        elapsed = time.time() - last_rob
        cooldown = ROB_COOLDOWN_MIN * 60
        if elapsed < cooldown:
            remaining = int((cooldown - elapsed) // 60) + 1
            return await message.reply_text(f"⏳ You're on cooldown. Try again in ~{remaining} min.")

        await db.set_last_rob(robber.id)

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
                f"🦹 {robber.first_name} robbed {stolen} {CURRENCY_EMOJI} from {victim.first_name}! (+{xp_gain} XP)"
            )
            await grant_xp(message, robber.id, xp_gain)
        else:
            fine = random.randint(10, 50)
            await db.add_balance(robber.id, -fine)
            await message.reply_text(
                f"🚓 {robber.first_name} got caught trying to rob {victim.first_name} and paid a {fine} {CURRENCY_EMOJI} fine!"
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
            f"🎉 {user.first_name} claimed this group's one-time reward: +{reward} {CURRENCY_EMOJI} {CURRENCY_NAME}!"
        )

    @app.on_message(filters.command("leaderboard"))
    async def leaderboard_cmd(client, message: Message):
        top = await db.get_leaderboard(10)
        if not top:
            return await message.reply_text("No one has any Bubbles yet!")

        lines = [f"🏆 {CURRENCY_NAME} Leaderboard"]
        for i, entry in enumerate(top, start=1):
            lines.append(f"{i}. {entry.get('first_name', 'Unknown')} — {entry.get('balance', 0)} {CURRENCY_EMOJI}")
        await message.reply_text("\n".join(lines))
