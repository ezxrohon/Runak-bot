# ============================================================
# 🫧🦋 ʀuɴAk - Owner-only admin commands
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import OWNER_ID


def register_admin_handlers(app: Client):

    @app.on_message(filters.private & filters.command("broadcast"))
    async def broadcast_cmd(client, message: Message):
        if message.from_user.id != OWNER_ID:
            return await message.reply_text("❌ Only the bot owner can use this command.")

        if not message.reply_to_message:
            return await message.reply_text("⚠️ Reply to a message to broadcast it.")

        text_to_send = message.reply_to_message.text or message.reply_to_message.caption
        if not text_to_send:
            return await message.reply_text("⚠️ The replied message has no text to send.")

        users = await db.get_all_users()
        sent, failed = 0, 0
        await message.reply_text(f"📢 Broadcasting to {len(users)} users...")

        for user_id in users:
            try:
                await client.send_message(user_id, text_to_send)
                sent += 1
            except Exception:
                failed += 1

        await message.reply_text(f"✅ Broadcast finished!\nSent: {sent}\nFailed: {failed}")

    @app.on_message(filters.private & filters.command("stats"))
    async def stats_cmd(client, message: Message):
        if message.from_user.id != OWNER_ID:
            return await message.reply_text("❌ Only the bot owner can use this command.")

        users = await db.get_all_users()
        await message.reply_text(f"💡 Total users: {len(users)}")
