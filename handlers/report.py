# ============================================================
# 🫧🦋 ʀuɴAk - Report
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError


def register_report_handlers(app: Client):

    @app.on_message(filters.group & filters.command("report"))
    async def report_cmd(client, message: Message):
        if not message.reply_to_message:
            return await message.reply_text("⚠️ Reply to the message you want to report.")

        reporter = message.from_user
        reported_user = message.reply_to_message.from_user
        reason = message.text.split(None, 1)[1] if len(message.command) > 1 else "No reason given"

        try:
            admins = []
            async for member in client.get_chat_members(message.chat.id):
                if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR) and not member.user.is_bot:
                    admins.append(member.user)

            mentions = " ".join(f"[{a.first_name}](tg://user?id={a.id})" for a in admins) or "admins"
            await message.reply_text(
                f"🚨 **Report**\n\n"
                f"📢 From: {reporter.first_name}\n"
                f"⚠️ Reported: {reported_user.first_name if reported_user else 'Unknown'}\n"
                f"📝 {reason}\n\n{mentions}"
            )
        except RPCError as e:
            await message.reply_text(f"❌ {e}")
