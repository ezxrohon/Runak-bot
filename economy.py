# ============================================================
# 🫧🦋 ʀuɴAk - Economy (Bubbles)
# ============================================================

import time
import random
from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import CURRENCY_NAME, CURRENCY_EMOJI, DAILY_REWARD, ROB_COOLDOWN_MIN


def register_economy_handlers(app: Client):

    @app.on_message(filters.command("balance"))
    async def balance_cmd(client, message: Message):
        target = message.from_user
        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
            await db.add_user(target.id, target.first_name)

        await db.add_user(target.id, target.first_name)
        bal = await db.get_balance(target.id)
        await message.reply_text(f"{CURRENCY_EMOJI} {target.first_name} has {bal} {CURRENCY_NAME}.")

    @app.on_message(filters.command("daily"))
    async def daily_cmd(client, message: Message):
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
        await message.reply_text(f"🎁 You claimed your daily {DAILY_REWARD} {CURRENCY_EMOJI} {CURRENCY_NAME}!")

    @app.on_message(filters.command("give"))
    async def give_cmd(client, message: Message):
        sender = message.from_user
        target = None
        amount = None

        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
            if len(message.command) > 1:
                amount = message.command[1]
        elif len(message.command) > 2:
            try:
                target = await client.get_users(message.command[1])
            except Exception:
                target = None
            amount = message.command[2]

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

        await message.reply_text(f"✅ {sender.first_name} sent {amount} {CURRENCY_EMOJI} to {target.first_name}!")

    @app.on_message(filters.command("rob"))
    async def rob_cmd(client, message: Message):
        robber = message.from_user
        if not message.reply_to_message or not message.reply_to_message.from_user:
            return await message.reply_text("⚠️ Reply to the user you want to rob.")

        victim = message.reply_to_message.from_user
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

        victim_balance = await db.get_balance(victim.id)
        if victim_balance < 20:
            return await message.reply_text(f"💸 {victim.first_name} is too broke to rob.")

        success = random.random() < 0.45  # 45% success rate
        if success:
            stolen = min(victim_balance, random.randint(10, max(11, victim_balance // 3)))
            await db.add_balance(victim.id, -stolen)
            await db.add_balance(robber.id, stolen)
            await message.reply_text(
                f"🦹 {robber.first_name} robbed {stolen} {CURRENCY_EMOJI} from {victim.first_name}!"
            )
        else:
            fine = random.randint(10, 50)
            await db.add_balance(robber.id, -fine)
            await message.reply_text(
                f"🚓 {robber.first_name} got caught trying to rob {victim.first_name} and paid a {fine} {CURRENCY_EMOJI} fine!"
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
