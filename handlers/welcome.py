# ============================================================
# 🫧🦋 ʀuɴAk - Welcome messages
# ============================================================

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
import db
from .common import is_admin

DEFAULT_WELCOME = "👋 Welcome {first_name} to {title}!"
logger = logging.getLogger(__name__)


def register_welcome_handlers(app: Client):

    @app.on_chat_member_updated()
    async def member_update(client: Client, cmu: ChatMemberUpdated):
        if not cmu.new_chat_member or cmu.new_chat_member.status != ChatMemberStatus.MEMBER:
            return
        if cmu.old_chat_member is not None:
            return  # only fire for brand-new joins, not re-promotions etc.

        user = cmu.new_chat_member.user
        if user.is_bot:
            return

        enabled = await db.get_welcome_status(cmu.chat.id)
        if not enabled:
            return

        text_template = await db.get_welcome_message(cmu.chat.id) or DEFAULT_WELCOME
        try:
            text = text_template.format(
                username=user.username or user.first_name,
                first_name=user.first_name,
                mention=f"[{user.first_name}](tg://user?id={user.id})",
                id=user.id,
                title=cmu.chat.title,
            )
        except (KeyError, IndexError):
            text = DEFAULT_WELCOME.format(first_name=user.first_name, title=cmu.chat.title)

        try:
            await client.send_message(cmu.chat.id, text)
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")

    @app.on_message(filters.group & filters.command("setwelcome"))
    async def set_welcome_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2:
            return await message.reply_text(
                "⚠️ Usage: /setwelcome <text>\nPlaceholders: {first_name} {mention} {id} {title}"
            )

        text = message.text.split(None, 1)[1]
        await db.set_welcome_message(message.chat.id, text)
        await message.reply_text("✅ Welcome message updated.")

    @app.on_message(filters.group & filters.command("welcome"))
    async def welcome_toggle_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2 or message.command[1].lower() not in ("on", "off"):
            return await message.reply_text("⚠️ Usage: /welcome on | off")

        status = message.command[1].lower() == "on"
        await db.set_welcome_status(message.chat.id, status)
        await message.reply_text(f"✅ Welcome messages turned {'ON' if status else 'OFF'}.")
