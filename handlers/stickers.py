# ============================================================
# 🫧🦋 ʀuɴAk - Sticker Reactions
# ============================================================
#
# Replies with a random sticker whenever someone sends the bot a sticker:
#   - In private chat: any sticker triggers a reply.
#   - In groups: only when the sticker is sent as a *reply to the bot's
#     own message* (otherwise every sticker anyone sends would trigger
#     a reply, which gets noisy fast).
#
# Sticker choice, in priority order:
#   1. A random sticker from the SAME PACK as the one the sender used,
#      looked up live from Telegram - this is the default behaviour,
#      no setup required.
#   2. STICKER_POOL below, if you want a manual fallback pool for
#      one-off stickers that don't belong to a named pack.
#   3. As a last resort, echoes the sender's own sticker back unchanged
#      (this only happens if step 1 AND 2 both come up empty - check
#      your bot's logs for a "Sticker pack lookup failed" warning if
#      you're always landing here).
# ============================================================

import logging
import random
from pyrogram import Client, filters, raw, types
from pyrogram.types import Message
import db

log = logging.getLogger(__name__)

# Optional manual fallback pool - only used when the sender's sticker
# has no pack (set_name) to pull from, or the pack lookup fails.
# Fill it via /stickerid (reply to a sticker) if you want one.
STICKER_POOL = []


async def _fetch_pack_stickers(client: Client, set_name: str):
    """Fetch every sticker in a pack by its short name. Tries the
    high-level helper first, falls back to a raw API call if that
    isn't available on this pyrogram build."""
    if hasattr(client, "get_stickers"):
        return await client.get_stickers(set_name)

    # Manual fallback: replicate what get_stickers does internally
    sticker_set = await client.invoke(
        raw.functions.messages.GetStickerSet(
            stickerset=raw.types.InputStickerSetShortName(short_name=set_name),
            hash=0,
        )
    )
    return [
        await types.Sticker._parse(client, doc, {type(a): a for a in doc.attributes})
        for doc in sticker_set.documents
    ]


async def pick_reply_sticker(client: Client, message: Message) -> str:
    """Pick a file_id to reply with: prefer a random sticker from the same
    pack as the one received, then STICKER_POOL, then echo it back."""
    sticker = message.sticker
    set_name = sticker.set_name

    if set_name:
        try:
            pack_stickers = await _fetch_pack_stickers(client, set_name)
        except Exception:
            log.warning("Sticker pack lookup failed for '%s'", set_name, exc_info=True)
            pack_stickers = []
        if pack_stickers:
            return random.choice(pack_stickers).file_id
    else:
        log.info("Sticker has no pack (set_name is empty) - can't pick from a pack for it.")

    if STICKER_POOL:
        return random.choice(STICKER_POOL)

    return sticker.file_id


def register_sticker_handlers(app: Client):

    @app.on_message(filters.command("stickerid"))
    async def stickerid_cmd(client, message: Message):
        target = message.reply_to_message
        if not target or not target.sticker:
            return await message.reply_text(
                "⚠️ Reply to a sticker with /stickerid to grab its file_id — "
                "useful only if you want a manual fallback in STICKER_POOL "
                "(handlers/stickers.py). Not required for normal use."
            )
        await message.reply_text(f"`{target.sticker.file_id}`")

    @app.on_message(filters.private & filters.sticker)
    async def sticker_reply_private(client, message: Message):
        reply_id = await pick_reply_sticker(client, message)
        await message.reply_sticker(reply_id)

    @app.on_message(filters.group & filters.sticker & filters.reply)
    async def sticker_reply_group(client, message: Message):
        replied = message.reply_to_message
        # Only react when the sticker is a reply to the bot's own message
        if not replied or not replied.from_user or not replied.from_user.is_self:
            return

        # Respect the group's sticker lock, if admins have enabled it
        locks = await db.get_locks(message.chat.id)
        if locks.get("sticker"):
            return

        reply_id = await pick_reply_sticker(client, message)
        await message.reply_sticker(reply_id)
