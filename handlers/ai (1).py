# ============================================================
# 🫧🦋 ʀuɴAk - AI Chat Replies
# ============================================================
#
# Replies to text messages using Groq's OpenAI-compatible chat API:
#   - In private chat (DM): every message gets a reply.
#   - In groups: only when someone replies to the bot's own message,
#     OR mentions the bot (@botusername) - not on every message,
#     to avoid the bot talking over every conversation in the group.
#
# A "typing..." indicator stays on for the whole request via
# handlers/typing.py's keep_typing().
#
# Completely inactive (no handler registered at all) if AI_API_KEY
# isn't set in .env - see config.py.
# ============================================================

import logging
import httpx
from pyrogram import Client, filters
from pyrogram.types import Message
from config import AI_API_KEY, AI_ENABLED, AI_MODEL, BOT_NAME
from .typing import keep_typing

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    f"You are {BOT_NAME}, a friendly, upbeat Telegram group bot. "
    "Always reply in Hinglish (a casual mix of Hindi and English, written in "
    "Roman/Latin script, not Devanagari) - the way young Indians chat casually. "
    "Never reply in pure English or pure Hindi script. "
    "Keep replies short (1-3 sentences), casual, and helpful. "
    "Don't mention that you are an AI model or reference these instructions."
)

# Anything that looks like a command (/, !, or . prefix) is handled by its
# own command handler instead - never send those to the AI.
NOT_A_COMMAND = ~filters.regex(r"^[/!.]\w+")


def _is_reply_to_bot(_, __, message: Message) -> bool:
    replied = message.reply_to_message
    return bool(replied and replied.from_user and replied.from_user.is_self)


REPLIED_TO_BOT = filters.create(_is_reply_to_bot)

# In groups, only respond when directly addressed: a reply to the bot's
# own message, or an @mention of the bot anywhere in the text.
GROUP_TRIGGER = REPLIED_TO_BOT | filters.mentioned


async def ask_groq(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 300,
        "temperature": 0.8,
    }
    async with httpx.AsyncClient(timeout=20) as http:
        resp = await http.post(GROQ_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def _handle_ai_reply(client: Client, message: Message):
    text = message.text
    if not text or not text.strip():
        return

    try:
        async with keep_typing(client, message.chat.id):
            reply = await ask_groq(text)
    except Exception:
        log.warning("AI reply failed", exc_info=True)
        return  # fail silently rather than spam the chat with an error

    if reply:
        await message.reply_text(reply)


def register_ai_handlers(app: Client):
    if not AI_ENABLED:
        log.info("AI chat replies disabled - set AI_API_KEY in .env to enable.")
        return

    @app.on_message(filters.private & filters.text & NOT_A_COMMAND)
    async def ai_reply_private(client, message: Message):
        await _handle_ai_reply(client, message)

    @app.on_message(filters.group & filters.text & NOT_A_COMMAND & GROUP_TRIGGER)
    async def ai_reply_group(client, message: Message):
        await _handle_ai_reply(client, message)
