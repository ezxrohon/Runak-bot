# ============================================================
# 🫧🦋 ʀuɴAk - Locks (block message types per group)
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import db

VALID_LOCKS = {"url", "sticker", "media", "username", "forward"}


def register_lock_handlers(app: Client):

    @app.on_message(filters.group & filters.command("lock"))
    async def lock_cmd(client, message: Message):
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2 or message.command[1].lower() not in VALID_LOCKS:
            return await message.reply_text(f"⚠️ Usage: /lock <type>\nTypes: {', '.join(VALID_LOCKS)}")

        lock_type = message.command[1].lower()
        await db.set_lock(message.chat.id, lock_type, True)
        await message.reply_text(f"🔒 Locked: {lock_type}")

    @app.on_message(filters.group & filters.command("unlock"))
    async def unlock_cmd(client, message: Message):
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2 or message.command[1].lower() not in VALID_LOCKS:
            return await message.reply_text(f"⚠️ Usage: /unlock <type>\nTypes: {', '.join(VALID_LOCKS)}")

        lock_type = message.command[1].lower()
        await db.set_lock(message.chat.id, lock_type, False)
        await message.reply_text(f"🔓 Unlocked: {lock_type}")

    @app.on_message(filters.group & filters.command("locks"))
    async def locks_list_cmd(client, message: Message):
        locks = await db.get_locks(message.chat.id)
        active = [k for k, v in locks.items() if v] or ["None"]
        await message.reply_text("🔒 Active locks:\n" + "\n".join(f"• {l}" for l in active))

    # ---- enforcement, runs after other command handlers ----
    @app.on_message(filters.group & ~filters.service, group=1)
    async def enforce_locks(client, message: Message):
        if not message.from_user:
            return
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                return
        except Exception:
            return

        locks = await db.get_locks(message.chat.id)
        if not locks:
            return

        if locks.get("url") and message.text:
            if message.entities and any(e.type in ("url", "text_link") for e in message.entities):
                return await message.delete()
            if "t.me/" in message.text.lower():
                return await message.delete()

        if locks.get("sticker") and message.sticker:
            return await message.delete()

        if locks.get("media") and (message.photo or message.video or message.document or message.animation):
            return await message.delete()

        if locks.get("username") and message.text and "@" in message.text:
            return await message.delete()

        if locks.get("forward") and message.forward_from:
            return await message.delete()
