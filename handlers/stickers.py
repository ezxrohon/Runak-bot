# ============================================================
# 🫧🦋 ʀuɴAk - Sticker Reactions
# ============================================================
#
# Replies with a random sticker whenever someone sends the bot a sticker:
#   - In private chat: any sticker triggers a reply.
#   - In groups: only when the sticker is sent as a *reply to the bot's
#     own message* (otherwise every sticker anyone sends would trigger
#     a reply, which gets noisy fast).
#
# Telegram stickers are referenced by file_id, not an uploadable file,
# so STICKER_POOL below needs to be filled with real file_ids.
# Use /stickerid (reply to any sticker) to grab one quickly.
# ============================================================

import random
from pyrogram import Client, filters
from pyrogram.types import Message
import db

# Paste sticker file_ids here, e.g.:
# STICKER_POOL = [
#     "CAACAgUAAxkBAAIB...",
#     "CAACAgUAAxkBAAIC...",
# ]
STICKER_POOL = []


def register_sticker_handlers(app: Client):

    @app.on_message(filters.command("stickerid"))
    async def stickerid_cmd(client, message: Message):
        target = message.reply_to_message
        if not target or not target.sticker:
            return await message.reply_text(
                "⚠️ Reply to a sticker with /stickerid to grab its file_id, "
                "then paste it into STICKER_POOL in handlers/stickers.py."
            )
        await message.reply_text(f"`{target.sticker.file_id}`")

    @app.on_message(filters.private & filters.sticker)
    async def sticker_reply_private(client, message: Message):
        if not STICKER_POOL:
            return
        await message.reply_sticker(random.choice(STICKER_POOL))

    @app.on_message(filters.group & filters.sticker & filters.reply)
    async def sticker_reply_group(client, message: Message):
        replied = message.reply_to_message
        # Only react when the sticker is a reply to the bot's own message
        if not replied or not replied.from_user or not replied.from_user.is_self:
            return

        if not STICKER_POOL:
            return

        # Respect the group's sticker lock, if admins have enabled it
        locks = await db.get_locks(message.chat.id)
        if locks.get("sticker"):
            return

        await message.reply_sticker(random.choice(STICKER_POOL))
