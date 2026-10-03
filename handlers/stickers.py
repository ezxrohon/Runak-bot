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

import asyncio
import logging
import random
from pyrogram import Client, filters, raw, types
from pyrogram.types import Message
import db
from .typing import keep_choosing_sticker

log = logging.getLogger(__name__)

# Optional manual fallback pool - only used when the sender's sticker
# has no pack (set_name) to pull from, or the pack lookup fails.
# Fill it via /stickerid (reply to a sticker) if you want one.
STICKER_POOL = []

# Curated packs (short name = the part after /addstickers/ in the pack's
# t.me link) the bot always mixes in as extra candidates, on top of
# whatever pack the sender's own sticker came from. Add/remove short
# names here - no code changes needed elsewhere.
CURATED_PACK_NAMES = [
    "ST_hPpsxPAvcYUmyO3g4oXI0CsI_pQHYZpsae348PP4_by_StickersPackRobot",
    "roh4nmusic",
    "ViralStickerPackPremiumEmojiOfficial244",
    "Unemployed_Mastodon_by_fStikBot",
]

# In-memory cache of {pack_short_name: [Sticker, ...]} so we only hit the
# Telegram API once per pack per process, not on every single reply.
_pack_cache: dict = {}
_pack_cache_lock = asyncio.Lock()

# Same reply-time budget as the AI chat replies (handlers/ai.py) - if
# picking a sticker (pack lookup over the network) takes longer than this,
# fall back instantly instead of leaving the user staring at "choosing a
# sticker..." indefinitely.
REPLY_TIME_LIMIT = 5


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


async def _get_cached_pack_stickers(client: Client, set_name: str):
    """Like _fetch_pack_stickers, but cached per pack for the life of the
    process - curated packs get looked up on every reply otherwise, which
    is unnecessary network traffic since pack contents rarely change."""
    if set_name in _pack_cache:
        return _pack_cache[set_name]
    async with _pack_cache_lock:
        if set_name in _pack_cache:  # someone else filled it while we waited
            return _pack_cache[set_name]
        try:
            stickers = await _fetch_pack_stickers(client, set_name)
        except Exception:
            log.warning("Sticker pack lookup failed for '%s'", set_name, exc_info=True)
            stickers = []
        _pack_cache[set_name] = stickers
        return stickers


async def pick_reply_sticker(client: Client, message: Message) -> str:
    """Pick a file_id to reply with, drawn at random from:
      - the same pack as the sticker the sender just sent (if it has one), and
      - every pack listed in CURATED_PACK_NAMES above,
    all pooled together. Falls back to STICKER_POOL, then echoes the
    sender's own sticker back, if that pool ends up empty (e.g. every
    pack lookup failed)."""
    sticker = message.sticker
    set_name = sticker.set_name

    candidates = []

    if set_name:
        candidates.extend(await _get_cached_pack_stickers(client, set_name))
    else:
        log.info("Sticker has no pack (set_name is empty) - can't pick from a pack for it.")

    for pack_name in CURATED_PACK_NAMES:
        candidates.extend(await _get_cached_pack_stickers(client, pack_name))

    if candidates:
        return random.choice(candidates).file_id

    if STICKER_POOL:
        return random.choice(STICKER_POOL)

    return sticker.file_id


async def _reply_with_sticker(client: Client, message: Message):
    """Shows the 'choosing a sticker...' indicator while picking a reply,
    capped at REPLY_TIME_LIMIT seconds so the bot never goes quiet for long."""
    try:
        async with keep_choosing_sticker(client, message.chat.id):
            reply_id = await asyncio.wait_for(
                pick_reply_sticker(client, message), timeout=REPLY_TIME_LIMIT
            )
    except asyncio.TimeoutError:
        log.warning("Sticker pick timed out in chat %s", message.chat.id)
        reply_id = message.sticker.file_id  # echo theirs back rather than stay silent
    await message.reply_sticker(reply_id)


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
        await _reply_with_sticker(client, message)

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

        await _reply_with_sticker(client, message)
