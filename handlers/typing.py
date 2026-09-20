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


async def _send_action(client: Client, chat_id: int, action: ChatAction = ChatAction.TYPING):
    try:
        await client.send_chat_action(chat_id, action)
    except Exception:
        # Non-fatal - some chats/permissions don't allow chat actions.
        log.debug("Couldn't send %s action in chat %s", action, chat_id, exc_info=True)


@asynccontextmanager
async def keep_chat_action(
    client: Client, chat_id: int, action: ChatAction = ChatAction.TYPING, interval: float = 4.0
):
    """Keep a chat action (typing..., choosing a sticker...) alive for the
    duration of a slow block of code (Telegram clears it after ~5s
    otherwise). Use it like:

        async with keep_chat_action(client, message.chat.id, ChatAction.TYPING):
            ... slow operation ...
    """

    async def _loop():
        while True:
            await _send_action(client, chat_id, action)
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


def keep_typing(client: Client, chat_id: int, interval: float = 4.0):
    """Shows Telegram's 'typing...' indicator - used for AI text replies."""
    return keep_chat_action(client, chat_id, ChatAction.TYPING, interval)


def keep_choosing_sticker(client: Client, chat_id: int, interval: float = 4.0):
    """Shows Telegram's 'choosing a sticker...' indicator - used while the
    sticker-reply handler is picking which sticker to send back."""
    return keep_chat_action(client, chat_id, ChatAction.CHOOSE_STICKER, interval)


def register_typing_handlers(app: Client):

    @app.on_message(COMMAND_TRIGGER, group=-1)
    async def show_typing_for_commands(client, message: Message):
        await _send_action(client, message.chat.id, ChatAction.TYPING)

    @app.on_message(filters.sticker, group=-1)
    async def show_choosing_sticker(client, message: Message):
        await _send_action(client, message.chat.id, ChatAction.CHOOSE_STICKER)
