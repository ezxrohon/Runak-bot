# ============================================================
# 🫧🦋 ʀuɴAk - Group Add/Remove Log
# ============================================================
#
# Posts to LOG_CHAT_ID whenever the bot itself is added to, or removed
# from, a group - so the owner can keep track of where the bot is
# running without needing to be in every group personally.
#
# Completely inactive (no handler registered at all) if LOG_CHAT_ID
# isn't set in .env - see config.py.
# ============================================================

import logging
from pyrogram import Client
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus, ChatType
from config import LOG_CHAT_ID, BOT_NAME

log = logging.getLogger(__name__)

# Statuses that mean "not actually in the chat".
INACTIVE_STATUSES = (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)


def _status(member):
    return member.status if member else None


def _chat_username_line(chat) -> str:
    return f"@{chat.username}" if chat.username else "Private"


async def _member_count(client: Client, chat_id: int) -> str:
    # Pyrogram renamed this method between major versions - try both
    # names rather than hard-coding one and breaking on the other.
    method = getattr(client, "get_chat_member_count", None) or getattr(
        client, "get_chat_members_count", None
    )
    if not method:
        return "Unknown"
    try:
        return str(await method(chat_id))
    except Exception:
        return "Unknown"


async def _chat_link(client: Client, chat, can_call_api: bool) -> str:
    """Best-effort invite link. Only attempts the export_chat_invite_link
    API call when can_call_api is True - once the bot has been removed
    from a chat it no longer has permission to do that, so the "removed"
    log skips straight to the username-based fallback."""
    if chat.username:
        return f"https://t.me/{chat.username}"
    if not can_call_api:
        return "Private group (no link)"
    try:
        return await client.export_chat_invite_link(chat.id)
    except Exception:
        return "Private group (no link)"


def register_grouplog_handlers(app: Client):
    if not LOG_CHAT_ID:
        log.info("Group add/remove logging disabled - set LOG_CHAT_ID in .env to enable.")
        return

    @app.on_chat_member_updated()
    async def bot_membership_changed(client: Client, cmu: ChatMemberUpdated):
        me = client.me
        if me is None:
            try:
                me = await client.get_me()
            except Exception:
                return

        new_member = cmu.new_chat_member
        old_member = cmu.old_chat_member
        subject = new_member or old_member
        if not subject or not subject.user or subject.user.id != me.id:
            return  # this update is about some other member, not the bot

        if cmu.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return

        old_status = _status(old_member)
        new_status = _status(new_member)
        was_in = old_status is not None and old_status not in INACTIVE_STATUSES
        is_in = new_status is not None and new_status not in INACTIVE_STATUSES

        if was_in == is_in:
            return  # e.g. admin rights changed but membership itself didn't

        chat = cmu.chat
        actor = cmu.from_user
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})" if actor else "Unknown"

        if is_in:
            link = await _chat_link(client, chat, can_call_api=True)
            members = await _member_count(client, chat.id)
            text = (
                f"🟢 ˹˹{BOT_NAME}˼ ᴀᴅᴅᴇᴅ ɪɴ ᴀ ɴᴇᴡ ɢʀᴏᴜᴘ\n\n"
                f"🔖 ᴄʜᴀᴛ ɴᴀᴍᴇ: {chat.title}\n"
                f"🆔 ᴄʜᴀᴛ ɪᴅ: {chat.id}\n"
                f"👤 ᴄʜᴀᴛ ᴜꜱᴇʀɴᴀᴍᴇ: {_chat_username_line(chat)}\n"
                f"🔗 ᴄʜᴀᴛ ʟɪɴᴋ: {link}\n"
                f"👥 ɢʀᴏᴜᴘ ᴍᴇᴍʙᴇʀs: {members}\n"
                f"🤵 ᴀᴅᴅᴇᴅ ʙʏ: {actor_mention}"
            )
        else:
            link = await _chat_link(client, chat, can_call_api=False)
            text = (
                f"🔴 ˹{BOT_NAME}˼ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴀ ɢʀᴏᴜᴘ\n\n"
                f"🔖 ᴄʜᴀᴛ ɴᴀᴍᴇ: {chat.title}\n"
                f"🆔 ᴄʜᴀᴛ ɪᴅ: {chat.id}\n"
                f"👤 ᴄʜᴀᴛ ᴜꜱᴇʀɴᴀᴍᴇ: {_chat_username_line(chat)}\n"
                f"🔗 ᴄʜᴀᴛ ʟɪɴᴋ: {link}\n"
                f"🚫 ʀᴇᴍᴏᴠᴇᴅ ʙʏ: {actor_mention}"
            )

        try:
            await client.send_message(LOG_CHAT_ID, text, disable_web_page_preview=True)
        except Exception:
            log.warning("Failed to send group log message", exc_info=True)
