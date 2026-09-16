# ============================================================
# 🫧🦋 ʀuɴAk - Anti-flood
# ============================================================
#
# Flood tracking is kept in memory (per-process) since it only needs to
# survive a few seconds - no need to round-trip to Firebase for every
# message. The on/off limit itself IS stored in Firebase via db.py so it
# persists across restarts.
# ============================================================

import time
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.errors import RPCError
import db
from .common import is_admin

WINDOW_SECONDS = 5
_recent_messages = defaultdict(list)  # {(chat_id, user_id): [timestamps]}


def register_antiflood_handlers(app: Client):

    @app.on_message(filters.group & filters.command("setflood"))
    async def setflood_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text("⚠️ Usage: /setflood <number>")

        limit = int(message.command[1])
        await db.set_flood_limit(message.chat.id, limit)
        await message.reply_text(f"✅ Flood limit set to {limit} messages / {WINDOW_SECONDS}s.")

    @app.on_message(filters.group & filters.command("flood"))
    async def flood_info_cmd(client, message: Message):
        limit = await db.get_flood_limit(message.chat.id)
        if limit is None:
            await message.reply_text("🌊 Flood protection is currently OFF.")
        else:
            await message.reply_text(f"🌊 Flood limit: {limit} messages / {WINDOW_SECONDS}s.")

    @app.on_message(filters.group & filters.command("noflood"))
    async def noflood_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        await db.set_flood_limit(message.chat.id, None)
        await message.reply_text("✅ Flood protection turned off.")

    @app.on_message(filters.group & filters.text, group=5)
    async def check_flood(client, message: Message):
        if not message.from_user:
            return

        limit = await db.get_flood_limit(message.chat.id)
        if not limit:
            return

        if await is_admin(client, message.chat.id, message.from_user.id):
            return

        key = (message.chat.id, message.from_user.id)
        now = time.time()
        recent = [t for t in _recent_messages[key] if now - t < WINDOW_SECONDS]
        recent.append(now)
        _recent_messages[key] = recent

        if len(recent) >= limit:
            _recent_messages[key] = []
            try:
                await message.chat.restrict_member(message.from_user.id, ChatPermissions())
                await message.reply_text(f"🌊 {message.from_user.first_name} was flooding the chat — muted.")
            except RPCError:
                pass
