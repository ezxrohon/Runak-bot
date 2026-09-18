# ============================================================
# 🫧🦋 ʀuɴAk - Notes
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db
from .common import is_admin


def register_notes_handlers(app: Client):

    @app.on_message(filters.group & filters.command("save"))
    async def save_note_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 3:
            return await message.reply_text("⚠️ Usage: /save <name> <text>")

        name = message.command[1]
        text = message.text.split(None, 2)[2]
        await db.save_note(message.chat.id, name, text)
        await message.reply_text(f"✅ Note **{name}** saved.")

    @app.on_message(filters.group & filters.command("get"))
    async def get_note_cmd(client, message: Message):
        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /get <name>")

        name = message.command[1]
        note = await db.get_note(message.chat.id, name)
        if not note:
            return await message.reply_text(f"❌ No note called '{name}'.")
        await message.reply_text(f"📝 **{name}**\n\n{note}")

    @app.on_message(filters.group & filters.command("notes"))
    async def list_notes_cmd(client, message: Message):
        notes = await db.get_all_notes(message.chat.id)
        if not notes:
            return await message.reply_text("📭 No notes saved yet.")
        lines = [f"• #{name}" for name in notes.keys()]
        await message.reply_text("📝 Saved notes:\n" + "\n".join(lines))

    @app.on_message(filters.group & filters.command("clear"))
    async def clear_note_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /clear <name>")

        name = message.command[1]
        await db.delete_note(message.chat.id, name)
        await message.reply_text(f"🗑️ Note **{name}** deleted.")

    @app.on_message(filters.group & filters.command("clearall"))
    async def clearall_notes_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        await db.clear_all_notes(message.chat.id)
        await message.reply_text("🗑️ All notes deleted.")

    # ---- #hashtag shortcut ----
    @app.on_message(filters.group & filters.text & ~filters.command([
        "save", "get", "notes", "clear", "clearall"
    ]), group=2)
    async def hashtag_note(client, message: Message):
        if not message.text:
            return
        for word in message.text.split():
            if word.startswith("#") and len(word) > 1:
                note = await db.get_note(message.chat.id, word[1:])
                if note:
                    await message.reply_text(f"📝 **{word[1:]}**\n\n{note}")
                    break
