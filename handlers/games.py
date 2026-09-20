# ============================================================
# 🫧🦋 ʀuɴAk - Games
# ============================================================

import random
from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message
import db
from config import CURRENCY_EMOJI
from .duels import start_rps_duel

RPS_CHOICES = ("rock", "paper", "scissors")
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

GUESS_REWARD = 100


def register_game_handlers(app: Client):

    @app.on_message(filters.command("rps"))
    async def rps_cmd(client, message: Message):
        # /rps rock|paper|scissors -> solo, play against the bot (unchanged).
        # /rps <amount> as a reply to someone -> PvP wagered duel (duels.py).
        if len(message.command) >= 2 and message.command[1].lower() in RPS_CHOICES:
            user_choice = message.command[1].lower()
            bot_choice = random.choice(RPS_CHOICES)

            if user_choice == bot_choice:
                result = "🤝 It's a tie!"
            elif RPS_BEATS[user_choice] == bot_choice:
                result = "🎉 You win!"
            else:
                result = "😅 I win!"

            return await message.reply_text(f"You: {user_choice}\nMe: {bot_choice}\n\n{result}")

        if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP) and len(message.command) >= 2 and message.command[1].isdigit():
            return await start_rps_duel(client, message)

        await message.reply_text(
            "⚠️ Usage:\n"
            "/rps rock|paper|scissors — play against me\n"
            "/rps <amount> (as a reply) — challenge someone for Bubbles"
        )

    @app.on_message(filters.command("guess"))
    async def guess_cmd(client, message: Message):
        user = message.from_user
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text("⚠️ Usage: /guess <number 1-100>")

        guess = int(message.command[1])
        if not (1 <= guess <= 100):
            return await message.reply_text("⚠️ Pick a number between 1 and 100.")

        answer = random.randint(1, 100)
        await db.add_user(user.id, user.first_name)

        if guess == answer:
            await db.add_balance(user.id, GUESS_REWARD)
            await message.reply_text(
                f"🎯 Spot on! The number was {answer}. You win {GUESS_REWARD} {CURRENCY_EMOJI}!"
            )
        elif abs(guess - answer) <= 5:
            reward = GUESS_REWARD // 4
            await db.add_balance(user.id, reward)
            await message.reply_text(f"🔥 So close! The number was {answer}. You win {reward} {CURRENCY_EMOJI}.")
        else:
            await message.reply_text(f"❌ Nope, the number was {answer}. Try again!")
