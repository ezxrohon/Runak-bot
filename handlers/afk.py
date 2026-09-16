# ============================================================
# 🫧🦋 ʀuɴAk - AFK
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db


def register_afk_handlers(app: Client):

    @app.on_message(filters.command(["afk", "brb"]))
    async def afk_cmd(client, message: Message):
        reason = message.text.split(None, 1)[1] if len(message.command) > 1 else "No reason given"
        await db.set_afk(message.from_user.id, reason)
        await message.reply_text(f"😴 {message.from_user.first_name} is now AFK.\n📝 {reason}")

    @app.on_message(filters.group & filters.text & ~filters.command(["afk", "brb"]), group=7)
    async def check_afk(client, message: Message):
        if not message.from_user:
            return

        # coming back from AFK
        was_afk = await db.get_afk(message.from_user.id)
        if was_afk:
            await db.clear_afk(message.from_user.id)
            await message.reply_text(f"👋 {message.from_user.first_name} is back!")
            return

        # replying to / mentioning someone who's AFK
        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
            afk_info = await db.get_afk(target.id)
            if afk_info:
                await message.reply_text(
                    f"😴 {target.first_name} is AFK.\n📝 {afk_info.get('reason', 'No reason given')}"
                )
