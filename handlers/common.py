# ============================================================
# 🫧🦋 ʀuɴAk - Shared helpers used across multiple handler files
# ============================================================

from pyrogram.enums import ChatMemberStatus, MessageEntityType
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
    """Get the target user from a reply or a mention/username/id argument.

    Telegram's Bot API doesn't always hand back a fully-populated
    reply_to_message (quoted replies, older messages, forum topics, etc. can
    arrive with the object present but .from_user missing, or missing
    entirely even though the client shows a reply). When that happens we
    re-fetch the message by id before giving up, since a direct get_messages
    call usually returns the full object.
    """
    reply = message.reply_to_message
    if reply:
        if reply.from_user:
            return reply.from_user
        if not reply.sender_chat:
            # Reply object came back incomplete - try to fetch it fresh.
            try:
                fetched = await client.get_messages(message.chat.id, reply.id)
                if fetched and fetched.from_user:
                    return fetched.from_user
            except RPCError:
                pass
        # A reply to an anonymous admin / channel post has no user to target.
        return None

    if len(message.command) > 1:
        arg = message.command[1]

        # A plain @username or numeric id.
        try:
            return await client.get_users(arg)
        except RPCError:
            pass

        # Mentioning someone with no @username shows up as a text_mention
        # entity carrying the full user object - filters.command strips it
        # from message.command, so check the raw entities instead.
        if message.entities:
            for entity in message.entities:
                if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
                    return entity.user
    return None


def format_protection_remaining(seconds: float) -> str:
    """Formats a countdown as 'Xd Yh' (rounds up to the next hour)."""
    seconds = max(0, seconds)
    total_hours = -(-int(seconds) // 3600)  # ceil to next hour
    days, hours = divmod(total_hours, 24)
    return f"{days}d {hours}h"
