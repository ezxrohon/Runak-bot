# ============================================================
# 🫧🦋 ʀuɴAk - Typing Indicator
# ============================================================
#
# Shows a "typing..." status right before the bot processes a
# command or a sticker, so replies feel more responsive instead
# of appearing instantly out of nowhere.
#
# Runs in its own handler group (-1, i.e. before everything else)
# so it never blocks or interferes with the real command handlers -
# they run independently in their own groups either way.
# ============================================================

import asyncio
import logging
from contextlib import asynccontextmanager
from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.types import Message

log = logging.getLogger(__name__)

# Matches any message that looks like a command (starts with "/")
COMMAND_TRIGGER = filters.text & filters.regex(r"^/\w+")


async def _send_typing(client: Client, chat_id: int):
    try:
        await client.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception:
        # Non-fatal - some chats/permissions don't allow chat actions.
        log.debug("Couldn't send typing action in chat %s", chat_id, exc_info=True)


@asynccontextmanager
async def keep_typing(client: Client, chat_id: int, interval: float = 4.0):
    """Keep the 'typing...' status alive for the duration of a slow block
    of code (Telegram clears it after ~5s otherwise). Use it like:

        async with keep_typing(client, message.chat.id):
            ... slow operation, e.g. /broadcast looping over every user ...
    """

    async def _loop():
        while True:
            await _send_typing(client, chat_id)
            await asyncio.sleep(interval)

    task = asyncio.create_task(_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def register_typing_handlers(app: Client):

    @app.on_message((COMMAND_TRIGGER | filters.sticker), group=-1)
    async def show_typing(client, message: Message):
        await _send_typing(client, message.chat.id)
