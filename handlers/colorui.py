# ============================================================
# 🫧🦋 ʀuɴAk - Colourful inline buttons
# ============================================================
#
# Telegram's Bot API (Feb 2026+) lets inline buttons carry a "style":
#   primary = blue, success = green, danger = red.
# Pyrogram 2.0.x talks MTProto and cannot send that field, so the menu
# is sent/edited by pyrogram as usual (plain buttons show up instantly)
# and this helper then re-sends the SAME keyboard through the Bot API
# with colours added. If that call ever fails, the plain buttons simply
# stay - nothing breaks.
# ============================================================

import logging

import httpx
from pyrogram.types import InlineKeyboardMarkup

from config import BOT_TOKEN

log = logging.getLogger(__name__)

_CYCLE = ("primary", "success", "danger")  # blue, green, red


def _style_for(btn, row: int, col: int, styles):
    if styles:
        try:
            return styles[row][col]
        except (IndexError, TypeError):
            pass
    if "Back" in (btn.text or ""):
        return "danger"
    return _CYCLE[(row + col) % 3]


def _to_api(markup: InlineKeyboardMarkup, styles=None) -> dict:
    rows = []
    for r, row in enumerate(markup.inline_keyboard):
        out = []
        for c, btn in enumerate(row):
            item = {"text": btn.text, "style": _style_for(btn, r, c, styles)}
            if btn.url:
                item["url"] = btn.url
            elif btn.callback_data is not None:
                data = btn.callback_data
                item["callback_data"] = data.decode() if isinstance(data, bytes) else data
            else:
                continue
            out.append(item)
        rows.append(out)
    return {"inline_keyboard": rows}


async def colorize(message, markup: InlineKeyboardMarkup, styles=None):
    """Re-apply `markup` to `message` with coloured buttons.
    `styles` (optional) is a nested list matching the keyboard layout,
    e.g. [["success"], ["primary", "danger"]]; otherwise colours cycle
    blue/green/red and any "Back" button is red."""
    if not BOT_TOKEN or message is None:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup",
                json={
                    "chat_id": message.chat.id,
                    "message_id": message.id,
                    "reply_markup": _to_api(markup, styles),
                },
            )
        if resp.status_code != 200:
            log.warning("Button colour update failed: %s", resp.text[:200])
    except Exception:
        log.warning("Button colour update failed", exc_info=True)
