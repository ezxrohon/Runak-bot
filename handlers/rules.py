# ============================================================
# 🫧🦋 ʀuɴAk - Rules
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
import db


def register_rules_handlers(app: Client):

    @app.on_message(filters.group & filters.command("setrules"))
    async def setrules_cmd(client, message: Message):
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text("❌ You need to be an admin to use this.")

        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /setrules <text>")

        text = message.text.split(None, 1)[1]
        await db.set_rules(message.chat.id, text)
        await message.reply_text("✅ Rules updated.")

    @app.on_message(filters.group & filters.command("rules"))
    async def rules_cmd(client, message: Message):
        rules_text = await db.get_rules(message.chat.id)
        if not rules_text:
            return await message.reply_text("❌ No rules set for this group yet.")
        await message.reply_text(f"📜 **Group Rules:**\n\n{rules_text}")

    @app.on_message(filters.group & filters.command("clearrules"))
    async def clearrules_cmd(client, message: Message):
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text("❌ You need to be an admin to use this.")
        await db.clear_rules(message.chat.id)
        await message.reply_text("✅ Rules cleared.")
