# ============================================================
# 🫧🦋 ʀuɴAk - PvP Duels (/ttt, /rps vs a player)
# ============================================================
#
# Wagered 1v1 challenges: reply to the person you want to challenge with
# /ttt <amount> or /rps <amount>. Only that specific person can accept.
# Draw = full refund to both. Otherwise the winner takes the pot minus
# BANK_TAX (see game_common.py) - a draw isn't taxed since nobody won it.
#
# /rps here is the wagered PvP version. The solo "play against the bot"
# /rps (a bare move word, no amount) still lives in games.py - see the
# dispatch check in rps_cmd there.
# ============================================================

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import DUEL_CHALLENGE_SECONDS, DUEL_TURN_SECONDS
from .game_common import take_wager, refund_wager, payout, pot_after_tax, money

CHALLENGE_SECONDS = DUEL_CHALLENGE_SECONDS
TURN_SECONDS = DUEL_TURN_SECONDS

# (chat_id, msg_id) -> duel state dict
DUELS: dict = {}

RPS_MOVES = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


def _mention(uid, name):
    return f"[{name}](tg://user?id={uid})"


def _p(state, uid):
    return state["challenger"] if state["challenger"]["id"] == uid else state["opponent"]


async def _challenge_timeout(chat_id, msg_id, client):
    await asyncio.sleep(CHALLENGE_SECONDS)
    key = (chat_id, msg_id)
    state = DUELS.get(key)
    if not state or state["status"] != "pending":
        return
    DUELS.pop(key, None)
    await refund_wager(state["challenger"]["id"], state["amount"])
    try:
        await client.edit_message_text(
            chat_id, msg_id,
            f"⌛ {state['opponent']['name']} didn't respond in time. "
            f"{money(state['amount'])} refunded to {state['challenger']['name']}.",
        )
    except Exception:
        pass


async def _issue_challenge(client: Client, message: Message, kind: str):
    challenger = message.from_user
    label = "Tic-Tac-Toe" if kind == "ttt" else "Rock-Paper-Scissors"

    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply_text(
            f"⚠️ Reply to the person you want to challenge: /{kind} <amount>"
        )
    opponent = message.reply_to_message.from_user

    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(f"⚠️ Usage (as a reply): /{kind} <amount>")
    amount = int(message.command[1])
    if amount <= 0:
        return await message.reply_text("⚠️ Amount must be positive.")
    if opponent.id == challenger.id:
        return await message.reply_text("❌ You can't challenge yourself.")
    if opponent.is_bot:
        return await message.reply_text("❌ You can't challenge a bot.")

    if not await take_wager(challenger.id, challenger.first_name, amount):
        return await message.reply_text(f"❌ Not enough Bubbles — you need {money(amount)}.")

    msg = await message.reply_text(
        f"⚔️ {_mention(challenger.id, challenger.first_name)} challenges "
        f"{_mention(opponent.id, opponent.first_name)} to {label} for {money(amount)} each!\n\n"
        f"⏳ {opponent.first_name}, accept within {CHALLENGE_SECONDS}s."
    )

    state = {
        "kind": kind,
        "chat_id": message.chat.id,
        "msg_id": msg.id,
        "amount": amount,
        "status": "pending",
        "challenger": {"id": challenger.id, "name": challenger.first_name},
        "opponent": {"id": opponent.id, "name": opponent.first_name},
    }
    DUELS[(message.chat.id, msg.id)] = state
    state["timeout_task"] = asyncio.create_task(_challenge_timeout(message.chat.id, msg.id, client))

    try:
        await msg.edit_reply_markup(
            InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Accept", callback_data=f"duelaccept:{message.chat.id}:{msg.id}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"dueldecline:{message.chat.id}:{msg.id}"),
            ]])
        )
    except Exception:
        pass


async def _forfeit(client, state, loser_id):
    """One side ran out of time - the other takes the pot minus tax, same
    as a normal win. Only used for stalls, not for a genuine draw."""
    key = (state["chat_id"], state["msg_id"])
    DUELS.pop(key, None)
    winner = state["opponent"] if loser_id == state["challenger"]["id"] else state["challenger"]
    loser = state["challenger"] if winner is state["opponent"] else state["opponent"]
    pot = state["amount"] * 2
    win_amount = pot_after_tax(pot)
    await payout(winner["id"], win_amount)
    try:
        await client.edit_message_text(
            state["chat_id"], state["msg_id"],
            f"⏰ {loser['name']} took too long and forfeits.\n"
            f"🏆 {winner['name']} wins {money(win_amount)}!",
        )
    except Exception:
        pass


async def _resolve_draw(client, state):
    key = (state["chat_id"], state["msg_id"])
    DUELS.pop(key, None)
    await refund_wager(state["challenger"]["id"], state["amount"])
    await refund_wager(state["opponent"]["id"], state["amount"])


# ============================================================
# ⭕ Tic-Tac-Toe
# ============================================================

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


def _ttt_winner(board):
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def _ttt_keyboard(chat_id, msg_id, board):
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            idx = r * 3 + c
            label = board[idx] or "▫️"
            row.append(InlineKeyboardButton(label, callback_data=f"tttmove:{chat_id}:{msg_id}:{idx}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def _ttt_turn_timeout(chat_id, msg_id, client, expected_uid):
    await asyncio.sleep(TURN_SECONDS)
    state = DUELS.get((chat_id, msg_id))
    if not state or state["status"] != "active" or state.get("turn") != expected_uid:
        return
    await _forfeit(client, state, expected_uid)


async def _ttt_start(client, state):
    state["status"] = "active"
    state["board"] = [None] * 9
    state["x_id"] = state["challenger"]["id"]
    state["o_id"] = state["opponent"]["id"]
    state["turn"] = state["x_id"]
    await _ttt_announce(client, state)


async def _ttt_announce(client, state):
    turn_name = _p(state, state["turn"])["name"]
    mark = "❌" if state["turn"] == state["x_id"] else "⭕"
    try:
        await client.edit_message_text(
            state["chat_id"], state["msg_id"],
            f"⭕ **Tic-Tac-Toe** — {state['challenger']['name']} (❌) vs {state['opponent']['name']} (⭕)\n"
            f"💰 Pot: {money(state['amount'] * 2)}\n\n"
            f"🎯 {turn_name}'s turn ({mark}) — {TURN_SECONDS}s",
            reply_markup=_ttt_keyboard(state["chat_id"], state["msg_id"], state["board"]),
        )
    except Exception:
        pass
    state["turn_task"] = asyncio.create_task(
        _ttt_turn_timeout(state["chat_id"], state["msg_id"], client, state["turn"])
    )


async def ttt_move_callback(client: Client, callback_query: CallbackQuery):
    _, chat_id_s, msg_id_s, idx_s = callback_query.data.split(":")
    key = (int(chat_id_s), int(msg_id_s))
    idx = int(idx_s)
    state = DUELS.get(key)

    if not state or state["status"] != "active":
        return await callback_query.answer("This match has ended.", show_alert=True)
    uid = callback_query.from_user.id
    if uid != state["turn"]:
        return await callback_query.answer("⏳ Not your turn!", show_alert=True)
    if state["board"][idx]:
        return await callback_query.answer("That cell's taken.", show_alert=True)

    if state.get("turn_task"):
        state["turn_task"].cancel()

    mark = "❌" if uid == state["x_id"] else "⭕"
    state["board"][idx] = mark
    await callback_query.answer()

    winner_mark = _ttt_winner(state["board"])
    if winner_mark:
        winner = state["challenger"] if winner_mark == "❌" else state["opponent"]
        loser = state["opponent"] if winner_mark == "❌" else state["challenger"]
        pot = state["amount"] * 2
        win_amount = pot_after_tax(pot)
        DUELS.pop(key, None)
        await payout(winner["id"], win_amount)
        try:
            await callback_query.message.edit_text(
                f"⭕ **Tic-Tac-Toe** — {state['challenger']['name']} (❌) vs {state['opponent']['name']} (⭕)\n\n"
                f"🏆 {winner['name']} wins {money(win_amount)}! (beat {loser['name']})",
                reply_markup=_ttt_keyboard(chat_id_s, msg_id_s, state["board"]),
            )
        except Exception:
            pass
        return

    if all(state["board"]):
        DUELS.pop(key, None)
        await _resolve_draw(client, state)
        try:
            await callback_query.message.edit_text(
                f"⭕ **Tic-Tac-Toe** — {state['challenger']['name']} (❌) vs {state['opponent']['name']} (⭕)\n\n"
                f"🤝 It's a draw! {money(state['amount'])} refunded to both.",
                reply_markup=_ttt_keyboard(chat_id_s, msg_id_s, state["board"]),
            )
        except Exception:
            pass
        return

    state["turn"] = state["o_id"] if uid == state["x_id"] else state["x_id"]
    await _ttt_announce(client, state)


# ============================================================
# ✊ Rock-Paper-Scissors (PvP)
# ============================================================

async def _rps_start(client, state):
    state["status"] = "active"
    state["choices"] = {}
    try:
        await client.edit_message_text(
            state["chat_id"], state["msg_id"],
            f"✊ **Rock-Paper-Scissors** — {state['challenger']['name']} vs {state['opponent']['name']}\n"
            f"💰 Pot: {money(state['amount'] * 2)}\n\n"
            f"🤐 Both players: pick your move privately below ({TURN_SECONDS}s).",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(emoji, callback_data=f"rpsmove:{state['chat_id']}:{state['msg_id']}:{move}")
                for move, emoji in RPS_MOVES.items()
            ]]),
        )
    except Exception:
        pass
    state["turn_task"] = asyncio.create_task(_rps_timeout(state["chat_id"], state["msg_id"], client))


async def _rps_timeout(chat_id, msg_id, client):
    await asyncio.sleep(TURN_SECONDS)
    key = (chat_id, msg_id)
    state = DUELS.get(key)
    if not state or state["status"] != "active":
        return

    picked = set(state["choices"].keys())
    both = {state["challenger"]["id"], state["opponent"]["id"]}
    missing = both - picked
    if len(missing) == 2:
        DUELS.pop(key, None)
        await _resolve_draw(client, state)
        try:
            await client.edit_message_text(
                chat_id, msg_id,
                f"⌛ Neither player picked in time. {money(state['amount'])} refunded to both.",
            )
        except Exception:
            pass
    elif len(missing) == 1:
        await _forfeit(client, state, missing.pop())


async def rps_move_callback(client: Client, callback_query: CallbackQuery):
    _, chat_id_s, msg_id_s, move = callback_query.data.split(":")
    key = (int(chat_id_s), int(msg_id_s))
    state = DUELS.get(key)

    if not state or state["status"] != "active":
        return await callback_query.answer("This match has ended.", show_alert=True)
    uid = callback_query.from_user.id
    if uid not in (state["challenger"]["id"], state["opponent"]["id"]):
        return await callback_query.answer("This isn't your match!", show_alert=True)
    if uid in state["choices"]:
        return await callback_query.answer("You've already locked in your move.", show_alert=True)

    state["choices"][uid] = move
    await callback_query.answer(f"Locked in {RPS_MOVES[move]} — waiting on your opponent...")

    if len(state["choices"]) < 2:
        return

    if state.get("turn_task"):
        state["turn_task"].cancel()
    DUELS.pop(key, None)

    c_id, o_id = state["challenger"]["id"], state["opponent"]["id"]
    c_move, o_move = state["choices"][c_id], state["choices"][o_id]
    reveal = (
        f"{state['challenger']['name']}: {RPS_MOVES[c_move]}\n"
        f"{state['opponent']['name']}: {RPS_MOVES[o_move]}\n\n"
    )

    if c_move == o_move:
        await _resolve_draw(client, state)
        text = reveal + f"🤝 It's a draw! {money(state['amount'])} refunded to both."
    else:
        winner = state["challenger"] if RPS_BEATS[c_move] == o_move else state["opponent"]
        pot = state["amount"] * 2
        win_amount = pot_after_tax(pot)
        await payout(winner["id"], win_amount)
        text = reveal + f"🏆 {winner['name']} wins {money(win_amount)}!"

    try:
        await callback_query.message.edit_text(f"✊ **Rock-Paper-Scissors**\n\n{text}")
    except Exception:
        pass


# ============================================================
# Accept / Decline (shared by both game kinds)
# ============================================================

async def duel_accept_callback(client: Client, callback_query: CallbackQuery):
    _, chat_id_s, msg_id_s = callback_query.data.split(":")
    key = (int(chat_id_s), int(msg_id_s))
    state = DUELS.get(key)

    if not state or state["status"] != "pending":
        return await callback_query.answer("This challenge has expired.", show_alert=True)
    if callback_query.from_user.id != state["opponent"]["id"]:
        return await callback_query.answer("This challenge isn't addressed to you!", show_alert=True)

    if not await take_wager(state["opponent"]["id"], state["opponent"]["name"], state["amount"]):
        return await callback_query.answer(f"❌ You need {money(state['amount'])} to accept.", show_alert=True)

    if state.get("timeout_task"):
        state["timeout_task"].cancel()
    await callback_query.answer("Challenge accepted!")

    if state["kind"] == "ttt":
        await _ttt_start(client, state)
    else:
        await _rps_start(client, state)


async def duel_decline_callback(client: Client, callback_query: CallbackQuery):
    _, chat_id_s, msg_id_s = callback_query.data.split(":")
    key = (int(chat_id_s), int(msg_id_s))
    state = DUELS.get(key)

    if not state or state["status"] != "pending":
        return await callback_query.answer("This challenge has expired.", show_alert=True)
    if callback_query.from_user.id != state["opponent"]["id"]:
        return await callback_query.answer("This challenge isn't addressed to you!", show_alert=True)

    if state.get("timeout_task"):
        state["timeout_task"].cancel()
    DUELS.pop(key, None)
    await refund_wager(state["challenger"]["id"], state["amount"])
    await callback_query.answer("Challenge declined.")
    try:
        await callback_query.message.edit_text(
            f"❌ {state['opponent']['name']} declined the challenge. "
            f"{money(state['amount'])} refunded to {state['challenger']['name']}."
        )
    except Exception:
        pass


def register_duel_handlers(app: Client):

    @app.on_message(filters.group & filters.command("ttt"))
    async def ttt_cmd(client, message: Message):
        await _issue_challenge(client, message, "ttt")

    app.on_callback_query(filters.regex(r"^duelaccept:"))(duel_accept_callback)
    app.on_callback_query(filters.regex(r"^dueldecline:"))(duel_decline_callback)
    app.on_callback_query(filters.regex(r"^tttmove:"))(ttt_move_callback)
    app.on_callback_query(filters.regex(r"^rpsmove:"))(rps_move_callback)


async def start_rps_duel(client: Client, message: Message):
    """Called from games.py's /rps dispatch when it's used as a PvP
    challenge (reply + amount) rather than the solo vs-bot game."""
    await _issue_challenge(client, message, "rps")
