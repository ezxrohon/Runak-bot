# ============================================================
# 🫧🦋 ʀuɴAk - Spam ban (short-burst detector, separate from anti-flood)
# ============================================================

import time
from datetime import datetime, timedelta
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.errors import RPCError
import db
from .common import is_admin

SPAM_WINDOW_SECONDS = 5
SPAM_LIMIT = 8
MUTE_MINUTES = 10
_spam_track = defaultdict(list)  # {(chat_id, user_id): [timestamps]}


def register_antispam_handlers(app: Client):

    @app.on_message(filters.group & filters.command("spamban"))
    async def spamban_cmd(client, message: Message):
        if len(message.command) < 2:
            status = await db.get_spamban(message.chat.id)
            return await message.reply_text(
                f"🛡️ Spam ban is currently {'ON' if status else 'OFF'}.\n"
                f"{SPAM_LIMIT}+ messages in {SPAM_WINDOW_SECONDS}s = {MUTE_MINUTES} min mute.\n"
                f"Usage: /spamban on | off"
            )

        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        arg = message.command[1].lower()
        if arg not in ("on", "off"):
            return await message.reply_text("⚠️ Usage: /spamban on | off")

        await db.set_spamban(message.chat.id, arg == "on")
        await message.reply_text(f"🛡️ Spam ban turned {'ON' if arg == 'on' else 'OFF'}.")

    @app.on_message(filters.group & filters.text, group=6)
    async def check_spam(client, message: Message):
        if not message.from_user:
            return

        enabled = await db.get_spamban(message.chat.id)
        if not enabled:
            return

        if await is_admin(client, message.chat.id, message.from_user.id):
            return

        key = (message.chat.id, message.from_user.id)
        now = time.time()
        recent = [t for t in _spam_track[key] if now - t < SPAM_WINDOW_SECONDS]
        recent.append(now)
        _spam_track[key] = recent

        if len(recent) >= SPAM_LIMIT:
            _spam_track[key] = []
            try:
                until = datetime.utcnow() + timedelta(minutes=MUTE_MINUTES)
                await message.chat.restrict_member(message.from_user.id, ChatPermissions(), until_date=until)
                await message.reply_text(
                    f"🛡️ {message.from_user.first_name} was spamming — muted for {MUTE_MINUTES} minutes."
                )
            except RPCError:
                pass
