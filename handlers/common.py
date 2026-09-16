# ============================================================
# 🫧🦋 ʀuɴAk - Shared helpers used across multiple handler files
# ============================================================

from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import RPCError
from pyrogram.types import Message

ADMIN_STATUSES = (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def is_admin(client, chat_id, user_id) -> bool:
    """True if user_id is an admin/owner of chat_id. Never raises -
    any RPC error (bot not in chat, bot not admin, etc.) is treated
    as 'not an admin' rather than crashing the handler."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ADMIN_STATUSES
    except RPCError:
        return False


async def resolve_target(client, message: Message):
    """Get the target user from a reply or a mention/username/id argument."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user

    if len(message.command) > 1:
        arg = message.command[1]
        try:
            return await client.get_users(arg)
        except RPCError:
            return None
    return None
