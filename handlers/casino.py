# ============================================================
# 🫧🦋 ʀuɴAk - Casino Machines (/jackpot, /mines, /roulette)
# ============================================================
#
# Single-player wager games with an instant payout straight to the
# wallet on a win. State for an in-progress /mines board lives in
# memory, keyed by (chat_id, message_id) of its own grid message - short
# rounds only, same trade-off as the other new games (see game_common.py).
# ============================================================

import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import CURRENCY_NAME, MINES_GRID_SIZE, MINES_COUNT
from .game_common import take_wager, payout, money

# ---- Jackpot (slots) ----
# (symbol, pick-weight, payout multiplier if all 3 match)
SLOT_SYMBOLS = [
    ("🍒", 30, 4),
    ("🍋", 25, 4),
    ("🔔", 20, 6),
    ("⭐", 15, 8),
    ("💎", 7, 12),
    ("7️⃣", 3, 20),
]
_SLOT_NAMES = [s for s, _, _ in SLOT_SYMBOLS]
_SLOT_WEIGHTS = [w for _, w, _ in SLOT_SYMBOLS]
_SLOT_PAYOUT = {s: p for s, _, p in SLOT_SYMBOLS}


def _spin_reels():
    return [random.choices(_SLOT_NAMES, weights=_SLOT_WEIGHTS)[0] for _ in range(3)]


def _jackpot_multiplier(reels) -> int:
    if reels[0] == reels[1] == reels[2]:
        return _SLOT_PAYOUT[reels[0]]
    if reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        return 2
    return 0


# ---- Mines ----
MINES_GRID = MINES_GRID_SIZE
MINES_TOTAL = MINES_GRID * MINES_GRID
DEFAULT_MINE_COUNT = MINES_COUNT
MINES_HOUSE_EDGE = 0.97

# (chat_id, message_id) -> game state
MINES_GAMES: dict = {}


def _next_mines_multiplier(current: float, mine_count: int, revealed_before: int) -> float:
    remaining = MINES_TOTAL - revealed_before
    safe_remaining = remaining - mine_count
    factor = remaining / safe_remaining
    return current * factor * MINES_HOUSE_EDGE


def _mines_keyboard(chat_id, msg_id, state, ended: bool):
    rows = []
    for r in range(MINES_GRID):
        row = []
        for c in range(MINES_GRID):
            idx = r * MINES_GRID + c
            if idx in state["revealed"]:
                row.append(InlineKeyboardButton("✅", callback_data="noop"))
            elif ended and idx in state["mines"]:
                row.append(InlineKeyboardButton("💣", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton("🟪", callback_data=f"mine:{chat_id}:{msg_id}:{idx}"))
        rows.append(row)
    if not ended:
        rows.append([
            InlineKeyboardButton(
                f"💰 Cash Out ({state['multiplier']:.2f}x = {int(state['amount'] * state['multiplier'])})",
                callback_data=f"minecash:{chat_id}:{msg_id}",
            )
        ])
    return InlineKeyboardMarkup(rows)


# ---- Roulette ----
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
ROULETTE_BETS = {"red", "black", "odd", "even", "low", "high"}


def _roulette_color(n: int) -> str:
    if n == 0:
        return "green"
    return "red" if n in RED_NUMBERS else "black"


def _roulette_multiplier(bet: str, spin: int):
    """Returns the payout multiplier for a bet against a spin result, or
    None if the bet string wasn't a recognised bet type at all."""
    bet = bet.lower()
    if bet.isdigit():
        n = int(bet)
        if not (0 <= n <= 36):
            return None
        return 36 if n == spin else 0

    if bet not in ROULETTE_BETS:
        return None

    color = _roulette_color(spin)
    if bet == "red":
        return 2 if color == "red" else 0
    if bet == "black":
        return 2 if color == "black" else 0
    if bet == "odd":
        return 2 if spin != 0 and spin % 2 == 1 else 0
    if bet == "even":
        return 2 if spin != 0 and spin % 2 == 0 else 0
    if bet == "low":
        return 2 if 1 <= spin <= 18 else 0
    if bet == "high":
        return 2 if 19 <= spin <= 36 else 0
    return None


def register_casino_handlers(app: Client):

    # ---- /jackpot ----

    @app.on_message(filters.command("jackpot"))
    async def jackpot_cmd(client, message: Message):
        user = message.from_user
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text("⚠️ Usage: /jackpot <amount>")

        amount = int(message.command[1])
        if amount <= 0:
            return await message.reply_text("⚠️ Amount must be positive.")

        if not await take_wager(user.id, user.first_name, amount):
            return await message.reply_text(f"❌ Not enough {CURRENCY_NAME} — you need {money(amount)}.")

        reels = _spin_reels()
        msg = await message.reply_text("🎰 [ ❓ | ❓ | ❓ ]\nSpinning...")
        shown = ["❓", "❓", "❓"]
        for i in range(3):
            await asyncio.sleep(0.6)
            shown[i] = reels[i]
            try:
                await msg.edit_text(f"🎰 [ {' | '.join(shown)} ]\nSpinning...")
            except Exception:
                pass

        mult = _jackpot_multiplier(reels)
        winnings = amount * mult
        if winnings:
            await payout(user.id, winnings)
            result = f"🎉 {mult}x payout — you win {money(winnings)}!"
        else:
            result = f"💸 No match — you lost {money(amount)}."

        final_text = f"🎰 [ {' | '.join(reels)} ]\n{result}"
        try:
            await msg.edit_text(final_text)
        except Exception:
            await message.reply_text(final_text)

    # ---- /mines ----

    @app.on_message(filters.command("mines"))
    async def mines_cmd(client, message: Message):
        user = message.from_user
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text(
                f"⚠️ Usage: /mines <amount> [mine count 1-10] (default {DEFAULT_MINE_COUNT})"
            )

        amount = int(message.command[1])
        if amount <= 0:
            return await message.reply_text("⚠️ Amount must be positive.")

        mine_count = DEFAULT_MINE_COUNT
        if len(message.command) > 2 and message.command[2].isdigit():
            mine_count = max(1, min(10, int(message.command[2])))

        if not await take_wager(user.id, user.first_name, amount):
            return await message.reply_text(f"❌ Not enough {CURRENCY_NAME} — you need {money(amount)}.")

        mines = set(random.sample(range(MINES_TOTAL), mine_count))
        state = {
            "owner_id": user.id,
            "owner_name": user.first_name,
            "amount": amount,
            "mines": mines,
            "mine_count": mine_count,
            "revealed": set(),
            "multiplier": 1.0,
        }

        msg = await message.reply_text(
            f"💣 {user.first_name}'s Mines — {mine_count} mines, {money(amount)} staked.\n"
            f"Tap a tile to reveal it, or cash out anytime.",
            reply_markup=None,
        )
        MINES_GAMES[(message.chat.id, msg.id)] = state
        await msg.edit_reply_markup(_mines_keyboard(message.chat.id, msg.id, state, ended=False))

    @app.on_callback_query(filters.regex(r"^mine:"))
    async def mine_tap_callback(client, callback_query: CallbackQuery):
        _, chat_id_s, msg_id_s, idx_s = callback_query.data.split(":")
        chat_id, msg_id, idx = int(chat_id_s), int(msg_id_s), int(idx_s)
        key = (chat_id, msg_id)
        state = MINES_GAMES.get(key)

        if not state:
            return await callback_query.answer("This round has already ended.", show_alert=True)
        if callback_query.from_user.id != state["owner_id"]:
            return await callback_query.answer("🚫 Not your board!", show_alert=True)
        if idx in state["revealed"]:
            return await callback_query.answer()

        if idx in state["mines"]:
            MINES_GAMES.pop(key, None)
            await callback_query.answer("💥 BOOM!", show_alert=True)
            await callback_query.message.edit_text(
                f"💥 {state['owner_name']} hit a mine! Lost {money(state['amount'])}.",
                reply_markup=_mines_keyboard(chat_id, msg_id, state, ended=True),
            )
            return

        revealed_before = len(state["revealed"])
        state["revealed"].add(idx)
        state["multiplier"] = _next_mines_multiplier(state["multiplier"], state["mine_count"], revealed_before)

        safe_total = MINES_TOTAL - state["mine_count"]
        if len(state["revealed"]) >= safe_total:
            # Cleared the whole board - auto cash-out at the final multiplier.
            winnings = int(state["amount"] * state["multiplier"])
            MINES_GAMES.pop(key, None)
            await payout(state["owner_id"], winnings)
            await callback_query.answer(f"🏆 Board cleared! +{winnings}", show_alert=True)
            await callback_query.message.edit_text(
                f"🏆 {state['owner_name']} cleared the board! Cashed out {money(winnings)} "
                f"({state['multiplier']:.2f}x).",
                reply_markup=_mines_keyboard(chat_id, msg_id, state, ended=True),
            )
            return

        await callback_query.answer(f"Safe! {state['multiplier']:.2f}x")
        try:
            await callback_query.message.edit_text(
                f"💣 {state['owner_name']}'s Mines — {state['mine_count']} mines, {money(state['amount'])} staked.\n"
                f"Current multiplier: {state['multiplier']:.2f}x — cash out anytime.",
                reply_markup=_mines_keyboard(chat_id, msg_id, state, ended=False),
            )
        except Exception:
            pass

    @app.on_callback_query(filters.regex(r"^minecash:"))
    async def mine_cashout_callback(client, callback_query: CallbackQuery):
        _, chat_id_s, msg_id_s = callback_query.data.split(":")
        chat_id, msg_id = int(chat_id_s), int(msg_id_s)
        key = (chat_id, msg_id)
        state = MINES_GAMES.get(key)

        if not state:
            return await callback_query.answer("This round has already ended.", show_alert=True)
        if callback_query.from_user.id != state["owner_id"]:
            return await callback_query.answer("🚫 Not your board!", show_alert=True)
        if not state["revealed"]:
            return await callback_query.answer("Reveal at least one tile first!", show_alert=True)

        winnings = int(state["amount"] * state["multiplier"])
        MINES_GAMES.pop(key, None)
        await payout(state["owner_id"], winnings)
        await callback_query.answer(f"💰 Cashed out {winnings}!", show_alert=True)
        await callback_query.message.edit_text(
            f"💰 {state['owner_name']} cashed out {money(winnings)} ({state['multiplier']:.2f}x).",
            reply_markup=_mines_keyboard(chat_id, msg_id, state, ended=True),
        )

    @app.on_callback_query(filters.regex("^noop$"))
    async def noop_callback(client, callback_query: CallbackQuery):
        await callback_query.answer()

    # ---- /roulette ----

    @app.on_message(filters.command("roulette"))
    async def roulette_cmd(client, message: Message):
        user = message.from_user
        if len(message.command) < 3 or not message.command[1].isdigit():
            return await message.reply_text(
                "⚠️ Usage: /roulette <amount> <bet>\n"
                "Bets: a number 0-36, or red / black / odd / even / low (1-18) / high (19-36)"
            )

        amount = int(message.command[1])
        bet = message.command[2]
        if amount <= 0:
            return await message.reply_text("⚠️ Amount must be positive.")

        spin = random.randint(0, 36)
        mult = _roulette_multiplier(bet, spin)
        if mult is None:
            return await message.reply_text(
                "⚠️ Unrecognised bet. Use a number 0-36, or red/black/odd/even/low/high."
            )

        if not await take_wager(user.id, user.first_name, amount):
            return await message.reply_text(f"❌ Not enough {CURRENCY_NAME} — you need {money(amount)}.")

        msg = await message.reply_text("🎡 Spinning the wheel...")
        for _ in range(2):
            await asyncio.sleep(0.5)
            try:
                await msg.edit_text(f"🎡 Spinning... {random.randint(0, 36)}?")
            except Exception:
                pass

        color = _roulette_color(spin)
        color_emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[color]
        winnings = amount * mult

        if winnings:
            await payout(user.id, winnings)
            result = f"🎉 You bet {bet} and won {money(winnings)}! ({mult}x)"
        else:
            result = f"💸 You bet {bet} and lost {money(amount)}."

        final_text = f"🎡 Ball lands on {spin} {color_emoji}\n{result}"
        try:
            await msg.edit_text(final_text)
        except Exception:
            await message.reply_text(final_text)
