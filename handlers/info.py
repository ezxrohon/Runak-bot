# ============================================================
# 🫧🦋 ʀuɴAk - Info & utility lookups
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError
from config import OWNER_USERNAME

STATUS_LABELS = {
    ChatMemberStatus.OWNER: "👑 Owner",
    ChatMemberStatus.ADMINISTRATOR: "⭐ Admin",
    ChatMemberStatus.MEMBER: "👤 Member",
    ChatMemberStatus.RESTRICTED: "🚫 Restricted",
    ChatMemberStatus.LEFT: "🚶 Left",
    ChatMemberStatus.BANNED: "🔨 Banned",
}


def register_info_handlers(app: Client):

    @app.on_message(filters.command("id"))
    async def id_cmd(client, message: Message):
        if message.reply_to_message and message.reply_to_message.from_user:
            u = message.reply_to_message.from_user
            await message.reply_text(f"👤 {u.first_name}\n🆔 `{u.id}`")
        else:
            await message.reply_text(
                f"👤 Your ID: `{message.from_user.id}`\n💬 Chat ID: `{message.chat.id}`"
            )

    @app.on_message(filters.group & filters.command("info"))
    async def info_cmd(client, message: Message):
        target = message.from_user
        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
        elif len(message.command) > 1:
            try:
                target = await client.get_users(message.command[1])
            except RPCError:
                pass

        try:
            member = await client.get_chat_member(message.chat.id, target.id)
            label = STATUS_LABELS.get(member.status, str(member.status))
            await message.reply_text(
                f"ℹ️ **User Info**\n\n"
                f"👤 {target.first_name}\n"
                f"🆔 `{target.id}`\n"
                f"🔗 @{target.username or 'N/A'}\n"
                f"📊 {label}"
            )
        except RPCError as e:
            await message.reply_text(f"❌ {e}")

    @app.on_message(filters.group & filters.command("adminlist"))
    async def adminlist_cmd(client, message: Message):
        try:
            admins = []
            async for member in client.get_chat_members(message.chat.id):
                if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
                    admins.append(member)
            if not admins:
                return await message.reply_text("No admins found (or I can't see the member list).")
            lines = ["👮 **Admins:**\n"]
            for a in admins:
                role = "👑" if a.status == ChatMemberStatus.OWNER else "⭐"
                lines.append(f"{role} {a.user.first_name}")
            await message.reply_text("\n".join(lines))
        except RPCError as e:
            await message.reply_text(f"❌ {e}")

    @app.on_message(filters.group & filters.command("chatinfo"))
    async def chatinfo_cmd(client, message: Message):
        chat = message.chat
        try:
            count = await client.get_chat_members_count(chat.id)
        except RPCError:
            count = "N/A"
        await message.reply_text(
            f"💬 **Chat Info**\n\n"
            f"📛 {chat.title}\n"
            f"🆔 `{chat.id}`\n"
            f"👥 Members: {count}\n"
            f"🔗 @{chat.username or 'N/A'}"
        )

    @app.on_message(filters.command("owner"))
    async def owner_cmd(client, message: Message):
        await message.reply_text(
            f"👑 **Bot Owner**\n\n🔗 [Contact owner](https://t.me/{OWNER_USERNAME})"
        )
