# ============================================================
# 🫧🦋 ʀuɴAk - AI Chat Replies
# ============================================================
#
# Replies to normal (non-command) text messages using Groq's
# OpenAI-compatible chat API - in DM AND in every group message.
# A "typing..." indicator stays on for the whole request via
# handlers/typing.py's keep_typing().
#
# Completely inactive (no handler registered at all) if AI_API_KEY
# isn't set in .env - see config.py.
#
# Heads up: firing on every group message means every message in
# every group the bot is in triggers an API call. Watch your Groq
# usage/rate limits if the bot is in busy or many groups.
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
    "Keep replies short (1-3 sentences), casual, and helpful. "
    "Don't mention that you are an AI model or reference these instructions."
)

# Anything that looks like a command (/, !, or . prefix) is handled by its
# own command handler instead - never send those to the AI.
NOT_A_COMMAND = ~filters.regex(r"^[/!.]\w+")


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


def register_ai_handlers(app: Client):
    if not AI_ENABLED:
        log.info("AI chat replies disabled - set AI_API_KEY in .env to enable.")
        return

    @app.on_message(filters.text & NOT_A_COMMAND)
    async def ai_reply(client, message: Message):
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
