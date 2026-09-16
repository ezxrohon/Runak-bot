# ============================================================
# 🫧🦋 ʀuɴAk - Link guard (auto-delete links + warn, separate from /lock url)
# ============================================================

import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError
import db

LINK_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/|bit\.ly/|tinyurl\.com/|"
    r"youtu\.be/|youtube\.com/|instagram\.com/|facebook\.com/|"
    r"twitter\.com/|x\.com/|wa\.me/|whatsapp\.com/)",
    re.IGNORECASE,
)


def register_linkguard_handlers(app: Client):

    @app.on_message(filters.group & filters.command("linkban"))
    async def linkban_cmd(client, message: Message):
        if len(message.command) < 2:
            status = await db.get_linkban(message.chat.id)
            return await message.reply_text(
                f"🔗 Link ban is currently {'ON' if status else 'OFF'}.\n"
                f"Usage: /linkban on | off"
            )

        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text("❌ You need to be an admin to use this.")

        arg = message.command[1].lower()
        if arg not in ("on", "off"):
            return await message.reply_text("⚠️ Usage: /linkban on | off")

        await db.set_linkban(message.chat.id, arg == "on")
        if arg == "on":
            await message.reply_text("🔗✅ Link ban is now ON — links get deleted and warned (3 warns = mute).")
        else:
            await message.reply_text("🔗❌ Link ban turned OFF.")

    @app.on_message(filters.group & filters.text, group=4)
    async def check_links(client, message: Message):
        if not message.text or not message.from_user:
            return

        enabled = await db.get_linkban(message.chat.id)
        if not enabled:
            return

        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return

        if not LINK_PATTERN.search(message.text):
            return

        try:
            await message.delete()
        except RPCError:
            pass

        count = await db.add_warn(message.chat.id, message.from_user.id)
        if count >= 3:
            try:
                await message.chat.ban_member(message.from_user.id)
                await db.reset_warns(message.chat.id, message.from_user.id)
                await client.send_message(
                    message.chat.id,
                    f"🚫 {message.from_user.first_name} kept sending links and has been banned.",
                )
            except RPCError:
                pass
        else:
            await client.send_message(
                message.chat.id,
                f"🔗❌ {message.from_user.first_name}, links aren't allowed here. Warning: {count}/3.",
            )
