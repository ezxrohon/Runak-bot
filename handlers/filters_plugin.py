# ============================================================
# 🫧🦋 ʀuɴAk - Filters (auto-reply on trigger words)
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db
from .common import is_admin


def register_filter_handlers(app: Client):

    @app.on_message(filters.group & filters.command("filter"))
    async def add_filter_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 3:
            return await message.reply_text("⚠️ Usage: /filter <word> <reply text>")

        word = message.command[1]
        reply = message.text.split(None, 2)[2]
        await db.add_filter(message.chat.id, word, reply)
        await message.reply_text(f"✅ Filter **{word}** added.")

    @app.on_message(filters.group & filters.command("filters"))
    async def list_filters_cmd(client, message: Message):
        f = await db.get_all_filters(message.chat.id)
        if not f:
            return await message.reply_text("📭 No filters set.")
        lines = [f"• `{word}`" for word in f.keys()]
        await message.reply_text("🔍 Active filters:\n" + "\n".join(lines))

    @app.on_message(filters.group & filters.command("stop"))
    async def stop_filter_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /stop <word>")

        word = message.command[1]
        await db.delete_filter(message.chat.id, word)
        await message.reply_text(f"✅ Filter **{word}** removed.")

    @app.on_message(filters.group & filters.command("stopall"))
    async def stopall_filters_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        await db.clear_all_filters(message.chat.id)
        await message.reply_text("🗑️ All filters removed.")

    @app.on_message(filters.group & filters.text & ~filters.command([
        "filter", "filters", "stop", "stopall"
    ]), group=3)
    async def check_filters(client, message: Message):
        if not message.text:
            return
        triggers = await db.get_all_filters(message.chat.id)
        if not triggers:
            return
        text = message.text.lower()
        for word, reply in triggers.items():
            if word in text:
                await message.reply_text(reply)
                break
