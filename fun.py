# ============================================================
# 🫧🦋 ʀuɴAk - Fun commands
# ============================================================

import random
from pyrogram import Client, filters
from pyrogram.types import Message

EIGHT_BALL = [
    "Yes, definitely.", "It is certain.", "Without a doubt.", "Ask again later.",
    "Cannot predict now.", "Don't count on it.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.", "Signs point to yes.",
]

QUOTES = [
    "The only way to do great work is to love what you do.",
    "Life is what happens when you're busy making other plans.",
    "It always seems impossible until it's done.",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "Do or do not. There is no try.",
]

ACTIONS = {
    "hug": "🤗 {a} hugs {b}!",
    "slap": "👋 {a} slaps {b}!",
    "pat": "🖐️ {a} pats {b} gently.",
}


def register_fun_handlers(app: Client):

    @app.on_message(filters.command("roll"))
    async def roll_cmd(client, message: Message):
        await message.reply_text(f"🎲 You rolled a {random.randint(1, 6)}!")

    @app.on_message(filters.command("flip"))
    async def flip_cmd(client, message: Message):
        await message.reply_text(f"🪙 It's {random.choice(['Heads', 'Tails'])}!")

    @app.on_message(filters.command("8ball"))
    async def eightball_cmd(client, message: Message):
        if len(message.command) < 2:
            return await message.reply_text("⚠️ Ask a question, e.g. /8ball will I win?")
        await message.reply_text(f"🎱 {random.choice(EIGHT_BALL)}")

    @app.on_message(filters.command("quote"))
    async def quote_cmd(client, message: Message):
        await message.reply_text(f"💬 \"{random.choice(QUOTES)}\"")

    for action, template in ACTIONS.items():
        def make_handler(action=action, template=template):
            async def handler(client, message: Message):
                actor = message.from_user.first_name
                if message.reply_to_message and message.reply_to_message.from_user:
                    target = message.reply_to_message.from_user.first_name
                else:
                    target = "the chat"
                await message.reply_text(template.format(a=actor, b=target))
            return handler

        app.on_message(filters.command(action))(make_handler())
