# ============================================================
# 🫧🦋 ʀuɴAk - Games
# ============================================================

import random
from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import CURRENCY_EMOJI

RPS_CHOICES = ("rock", "paper", "scissors")
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

GUESS_REWARD = 100


def register_game_handlers(app: Client):

    @app.on_message(filters.command("rps"))
    async def rps_cmd(client, message: Message):
        if len(message.command) < 2 or message.command[1].lower() not in RPS_CHOICES:
            return await message.reply_text("⚠️ Usage: /rps rock|paper|scissors")

        user_choice = message.command[1].lower()
        bot_choice = random.choice(RPS_CHOICES)

        if user_choice == bot_choice:
            result = "🤝 It's a tie!"
        elif RPS_BEATS[user_choice] == bot_choice:
            result = "🎉 You win!"
        else:
            result = "😅 I win!"

        await message.reply_text(f"You: {user_choice}\nMe: {bot_choice}\n\n{result}")

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
