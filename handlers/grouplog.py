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
import time
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, Message
from pyrogram.errors import RPCError
from pyrogram.enums import ChatMemberStatus, ChatType
from config import LOG_CHAT_ID, OWNER_ID, BOT_NAME

log = logging.getLogger(__name__)

# Statuses that mean "not actually in the chat".
INACTIVE_STATUSES = (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)

# Dedup guard: a plain group joining can fire BOTH a service message
# ("X added the bot") AND, if it's actually a supergroup, a
# ChatMemberUpdated event for the same join - without this we'd post the
# same "added"/"removed" log twice. Keyed by (chat_id, "added"/"removed"),
# value is the time.monotonic() it was last posted; entries older than
# _DEDUP_WINDOW are treated as a genuinely new event (e.g. re-added later).
_recent_events: dict = {}
_DEDUP_WINDOW = 30  # seconds


def _already_logged(chat_id: int, kind: str) -> bool:
    now = time.monotonic()
    key = (chat_id, kind)
    last = _recent_events.get(key)
    _recent_events[key] = now
    return last is not None and (now - last) < _DEDUP_WINDOW


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


async def _post_log(client: Client, text: str):
    try:
        await client.send_message(LOG_CHAT_ID, text, disable_web_page_preview=True)
    except (ValueError, KeyError):
        log.warning(
            "Failed to send group log message: LOG_CHAT_ID (%s) has no cached "
            "peer yet - send any message inside that log chat once (e.g. /id) "
            "so the bot can resolve it, then this will start working.",
            LOG_CHAT_ID,
        )
    except Exception:
        log.warning("Failed to send group log message", exc_info=True)


async def _log_added(client: Client, chat, actor_mention: str):
    if _already_logged(chat.id, "added"):
        return
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
    await _post_log(client, text)


async def _log_removed(client: Client, chat, actor_mention: str):
    if _already_logged(chat.id, "removed"):
        return
    link = await _chat_link(client, chat, can_call_api=False)
    text = (
        f"🔴 ˹{BOT_NAME}˼ ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ᴀ ɢʀᴏᴜᴘ\n\n"
        f"🔖 ᴄʜᴀᴛ ɴᴀᴍᴇ: {chat.title}\n"
        f"🆔 ᴄʜᴀᴛ ɪᴅ: {chat.id}\n"
        f"👤 ᴄʜᴀᴛ ᴜꜱᴇʀɴᴀᴍᴇ: {_chat_username_line(chat)}\n"
        f"🔗 ᴄʜᴀᴛ ʟɪɴᴋ: {link}\n"
        f"🚫 ʀᴇᴍᴏᴠᴇᴅ ʙʏ: {actor_mention}"
    )
    await _post_log(client, text)


def register_grouplog_handlers(app: Client):
    if not LOG_CHAT_ID:
        log.info("Group add/remove logging disabled - set LOG_CHAT_ID in .env to enable.")
        return

    # Common misconfiguration: pasting a group's plain numeric id (e.g. from
    # /id) instead of its full -100... form. get_chat_member_count etc. will
    # fail against the former, which is a frequent cause of "nothing gets
    # posted to the log channel" with no obvious error in the console.
    if LOG_CHAT_ID > 0:
        log.warning(
            "LOG_CHAT_ID (%s) is positive - group/supergroup chat ids are "
            "negative (usually starting with -100). Double check the value "
            "in your .env.",
            LOG_CHAT_ID,
        )

    @app.on_message(filters.private & filters.command("testlog") & filters.user(OWNER_ID))
    async def testlog_cmd(client: Client, message: Message):
        """Owner-only: sends a test message straight to LOG_CHAT_ID and
        reports back exactly what happened, so a broken log channel can be
        diagnosed from Telegram instead of trawling server logs."""
        try:
            await client.send_message(LOG_CHAT_ID, "🧪 Test message from /testlog.")
        except RPCError as e:
            await message.reply_text(
                f"❌ Couldn't send to LOG_CHAT_ID ({LOG_CHAT_ID}): {e}\n\n"
                "Common causes: the bot isn't a member of that chat, the id is "
                "wrong (must be the full -100... form for groups/channels), "
                "or the bot was kicked/banned from it."
            )
        except (ValueError, KeyError) as e:
            # Pyrogram (MTProto) can only message a chat it already has a
            # cached peer/access_hash for - which it only gets by *receiving*
            # an update from that chat. Freshly adding the bot to a group
            # isn't enough on its own if nothing has been sent there since.
            await message.reply_text(
                f"❌ Couldn't send to LOG_CHAT_ID ({LOG_CHAT_ID}): {e}\n\n"
                "I don't have that chat cached yet - this happens when nothing's "
                "been sent there since the bot joined. Send any message (e.g. "
                "/id) inside that log group first, then try /testlog again."
            )
        except Exception as e:
            log.warning("Unexpected /testlog failure", exc_info=True)
            await message.reply_text(f"❌ Unexpected error sending to LOG_CHAT_ID ({LOG_CHAT_ID}): {e}")
        else:
            await message.reply_text(f"✅ Sent successfully to {LOG_CHAT_ID}.")

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
            await _log_added(client, chat, actor_mention)
        else:
            await _log_removed(client, chat, actor_mention)

    # ------------------------------------------------------------
    # Fallback path: plain (non-super) groups don't reliably emit a
    # ChatMemberUpdated event for the bot's own join - Telegram only sends
    # a normal service message there. Supergroups usually fire both, so
    # _already_logged() above dedupes if this and the handler above both
    # catch the same join.
    # ------------------------------------------------------------
    @app.on_message(filters.new_chat_members)
    async def bot_added_via_service_message(client: Client, message: Message):
        me = client.me
        if me is None:
            try:
                me = await client.get_me()
            except Exception:
                return
        if not any(u.id == me.id for u in message.new_chat_members):
            return  # someone else joined, not the bot
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return
        actor = message.from_user
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})" if actor else "Unknown"
        await _log_added(client, message.chat, actor_mention)

    @app.on_message(filters.left_chat_member)
    async def bot_removed_via_service_message(client: Client, message: Message):
        me = client.me
        if me is None:
            try:
                me = await client.get_me()
            except Exception:
                return
        if not message.left_chat_member or message.left_chat_member.id != me.id:
            return  # someone else left, not the bot
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return
        actor = message.from_user
        actor_mention = f"[{actor.first_name}](tg://user?id={actor.id})" if actor else "Unknown"
        await _log_removed(client, message.chat, actor_mention)
