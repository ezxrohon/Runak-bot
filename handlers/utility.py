# ============================================================
# 🫧🦋 ʀuɴAk - Utility
# ============================================================

import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from .common import is_admin

ALLOWED_CALC_CHARS = set("0123456789+-*/.() ")


def register_utility_handlers(app: Client):

    @app.on_message(filters.command("ping"))
    async def ping_cmd(client, message: Message):
        start = time.time()
        sent = await message.reply_text("🏓 Pinging...")
        ms = round((time.time() - start) * 1000, 2)
        await sent.edit_text(f"🏓 Pong! {ms}ms")

    @app.on_message(filters.command("calc"))
    async def calc_cmd(client, message: Message):
        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /calc 5+3*2")

        expr = message.text.split(None, 1)[1]
        if not all(c in ALLOWED_CALC_CHARS for c in expr):
            return await message.reply_text("❌ Only numbers and + - * / ( ) are allowed.")

        try:
            # eval is safe here because we've already restricted the
            # character set to digits/operators/parentheses above.
            result = eval(expr, {"__builtins__": {}}, {})
            await message.reply_text(f"🧮 `{expr}` = **{result}**")
        except Exception:
            await message.reply_text("❌ Invalid expression.")

    @app.on_message(filters.group & filters.command("echo"))
    async def echo_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ Only admins can use this.")

        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /echo <text>")

        text = message.text.split(None, 1)[1]
        try:
            await message.delete()
        except Exception:
            pass
        await client.send_message(message.chat.id, text)

    @app.on_message(filters.command("time"))
    async def time_cmd(client, message: Message):
        await message.reply_text(f"🕐 {datetime.utcnow().strftime('%d %B %Y, %H:%M UTC')}")
