# ============================================================
# 🫧🦋 ʀuɴAk - Chat activity tracking
# ============================================================
#
# Bots can't list a supergroup's full member list on demand, so instead
# we record who's active in each group as messages come in. This is what
# lets /bleaderboard and /kleaderboard scope down to "this group" instead
# of the whole bot's user base (/gleaderboard, /gbkboard).
#
# Runs at group=-1 (same tier as the typing indicator) so it never
# blocks any other handler - it just quietly notes "this user is in this
# chat" and lets the update carry on to whatever actually handles it.
# ============================================================

import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import db

log = logging.getLogger(__name__)


def register_tracking_handlers(app: Client):

    @app.on_message(filters.group, group=-1)
    async def track_chat_member(client: Client, message: Message):
        user = message.from_user
        if not user or user.is_bot:
            return
        try:
            await db.record_chat_member(message.chat.id, user.id)
        except Exception:
            log.debug("Couldn't record chat member", exc_info=True)
