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


async def _user_from_reply(client, message: Message):
    """Resolve the user from message.reply_to_message only - handles
    Telegram's occasionally-incomplete reply objects (quoted replies,
    older messages, forum topics) by re-fetching. Returns None if there's
    no reply, or the reply has no resolvable user (e.g. an anonymous
    admin / channel post)."""
    reply = message.reply_to_message
    if not reply:
        return None
    if reply.from_user:
        return reply.from_user
    if not reply.sender_chat:
        try:
            fetched = await client.get_messages(message.chat.id, reply.id)
            if fetched and fetched.from_user:
                return fetched.from_user
        except RPCError:
            pass
    return None


async def resolve_target(client, message: Message):
    """Get the target user from a reply or a mention/username/id argument."""
    reply = message.reply_to_message
    if reply:
        return await _user_from_reply(client, message)

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


async def resolve_reply_target(client, message: Message):
    """Like resolve_target, but reply-only - no mention/username fallback.
    Used for commands where the target must be an actual tap-and-reply on
    their message (/rob, /kill), not just a bare @username thrown at the
    bot from anywhere in the chat."""
    return await _user_from_reply(client, message)


def format_protection_remaining(seconds: float) -> str:
    """Formats a countdown as 'Xd Yh' (rounds up to the next hour)."""
    seconds = max(0, seconds)
    total_hours = -(-int(seconds) // 3600)  # ceil to next hour
    days, hours = divmod(total_hours, 24)
    return f"{days}d {hours}h"


# ------------------------------------------------------------
# Small caps text (same unicode "Latin Letter Small Capital" style
# already used everywhere else in this bot - BOT_NAME, admin titles,
# grouplog messages, etc). Only maps a-z / A-Z; every other character
# (digits, punctuation, emoji, Hindi/Devanagari, etc) passes through
# unchanged since there's no small-caps equivalent for them.
# ------------------------------------------------------------
_SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
)


def to_small_caps(text: str) -> str:
    """Converts a-z (case-insensitively) to small-caps unicode letters."""
    if not text:
        return text
    return text.lower().translate(_SMALL_CAPS_MAP)
