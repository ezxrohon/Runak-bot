# ============================================================
# 🫧🦋 ʀuɴAk - Card Game (/card, /bet, /flip)
# ============================================================
#
# Lobby-based multiplayer card game. Everyone's 4-card hand sums to the
# exact same total (see deal_hands below) so the game is pure nerve, not
# a better/worse deal - whoever reveals the single highest card wins the
# whole pot. Every card value used is unique across the entire game, so
# a tie on the reveal is mathematically impossible.
#
# State is in-memory only (one lobby/round per chat_id) - short-lived by
# design, resets on a bot restart same as the other new games.
# ============================================================

import asyncio
import random
import time
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import db
from config import (
    CURRENCY_EMOJI,
    CURRENCY_NAME,
    CARD_LOBBY_SECONDS,
    CARD_TURN_SECONDS,
    CARD_MIN_PLAYERS,
    CARD_MAX_PLAYERS,
)
from .game_common import take_wager, refund_wager, payout, money

log = logging.getLogger(__name__)

MIN_PLAYERS = CARD_MIN_PLAYERS
MAX_PLAYERS = CARD_MAX_PLAYERS
LOBBY_SECONDS = CARD_LOBBY_SECONDS
TURN_SECONDS = CARD_TURN_SECONDS
SLOTS = "abcd"

# chat_id -> lobby/game state dict
GAMES: dict = {}


def deal_hands(n_players: int):
    """Deal n_players hands of 4 unique cards each, every hand summing to
    the exact same total. Trick: pair up card value v with its complement
    (total+1-v) - every such pair sums to a constant, so giving each
    player exactly 2 complementary pairs gives everyone the same 4-card
    sum, guaranteed, while still using every value in 1..4n exactly once."""
    total_cards = 4 * n_players
    complement = total_cards + 1
    half = total_cards // 2  # == 2 * n_players, one pair count per player * 2
    pairs = [(v, complement - v) for v in range(1, half + 1)]
    random.shuffle(pairs)

    hands = []
    for i in range(n_players):
        p1, p2 = pairs[2 * i], pairs[2 * i + 1]
        cards = [p1[0], p1[1], p2[0], p2[1]]
        random.shuffle(cards)
        hands.append(cards)
    return hands


async def _cancel_lobby(chat_id, client, reason: str):
    game = GAMES.pop(chat_id, None)
    if not game:
        return
    for p in game["players"]:
        await refund_wager(p["id"], game["amount"])
    names = ", ".join(p["name"] for p in game["players"])
    try:
        await client.send_message(
            chat_id,
            f"❌ Card Game cancelled — {reason}\n"
            f"💸 Refunded {money(game['amount'])} to: {names}",
        )
    except Exception:
        pass


async def _lobby_timeout(chat_id, client):
    await asyncio.sleep(LOBBY_SECONDS)
    game = GAMES.get(chat_id)
    if not game or game["phase"] != "lobby":
        return  # already filled/started or already cancelled
    await _cancel_lobby(chat_id, client, "not enough players joined in time.")


def _hand_view(hand, flipped_value):
    lines = []
    for letter, value in zip(SLOTS, hand):
        marker = " (flipped)" if flipped_value == value else ""
        lines.append(f"{letter}: 🎴 {value}{marker}")
    return "\n".join(lines)


async def _announce_turn(chat_id, client, game):
    uid = game["turn_order"][game["turn_index"]]
    name = next(p["name"] for p in game["players"] if p["id"] == uid)
    try:
        await client.send_message(
            chat_id,
            f"🎯 {name}'s turn! Use /flip a/b/c/d within {TURN_SECONDS}s.\n"
            f"(Tap 👀 View My Hand above if you need a reminder.)",
        )
    except Exception:
        pass
    game["turn_task"] = asyncio.create_task(_turn_timeout(chat_id, client, uid))


async def _turn_timeout(chat_id, client, expected_uid):
    await asyncio.sleep(TURN_SECONDS)
    game = GAMES.get(chat_id)
    if not game or game["phase"] != "playing":
        return
    if game["turn_order"][game["turn_index"]] != expected_uid:
        return  # they already moved, this stale timer doesn't apply anymore
    # Auto-flip a random card for whoever stalled, so the game can't hang.
    hand = game["hands"][expected_uid]
    idx = random.randrange(4)
    value = hand[idx]
    name = next(p["name"] for p in game["players"] if p["id"] == expected_uid)
    try:
        await client.send_message(
            chat_id,
            f"⏰ {name} took too long — auto-flipped {SLOTS[idx]}: 🎴 {value}",
        )
    except Exception:
        pass
    await _resolve_flip(chat_id, client, expected_uid, value)


async def _resolve_flip(chat_id, client, uid, value):
    game = GAMES.get(chat_id)
    if not game:
        return
    game["flipped"][uid] = value
    game["turn_index"] += 1

    if game["turn_index"] >= len(game["turn_order"]):
        await _finish_game(chat_id, client, game)
        return

    await _announce_turn(chat_id, client, game)


async def _finish_game(chat_id, client, game):
    GAMES.pop(chat_id, None)
    winner_id = max(game["flipped"], key=lambda uid: game["flipped"][uid])
    winner = next(p for p in game["players"] if p["id"] == winner_id)
    pot = game["amount"] * len(game["players"])
    await payout(winner_id, pot)

    lines = ["🏆 **Card Game Results**", ""]
    for p in game["players"]:
        crown = " 👑" if p["id"] == winner_id else ""
        lines.append(f"{p['name']}: 🎴 {game['flipped'][p['id']]}{crown}")
    lines.append("")
    lines.append(f"🎉 {winner['name']} takes the pot: {money(pot)}!")
    try:
        await client.send_message(chat_id, "\n".join(lines))
    except Exception:
        pass


def register_cardgame_handlers(app: Client):

    @app.on_message(filters.group & filters.command("card"))
    async def card_cmd(client, message: Message):
        chat_id = message.chat.id
        if chat_id in GAMES:
            return await message.reply_text("⚠️ There's already a Card Game running in this group.")

        if len(message.command) < 3 or not message.command[1].isdigit() or not message.command[2].isdigit():
            return await message.reply_text("⚠️ Usage: /card <amount> <players>  (e.g. /card 500 4)")

        amount = int(message.command[1])
        required = int(message.command[2])
        if amount <= 0:
            return await message.reply_text("⚠️ Amount must be positive.")
        if not (MIN_PLAYERS <= required <= MAX_PLAYERS):
            return await message.reply_text(f"⚠️ Players must be between {MIN_PLAYERS} and {MAX_PLAYERS}.")

        starter = message.from_user
        if not await take_wager(starter.id, starter.first_name, amount):
            return await message.reply_text(f"❌ Not enough {CURRENCY_NAME} — you need {money(amount)}.")

        GAMES[chat_id] = {
            "phase": "lobby",
            "amount": amount,
            "required": required,
            "players": [{"id": starter.id, "name": starter.first_name}],
            "created_at": time.time(),
        }
        GAMES[chat_id]["lobby_task"] = asyncio.create_task(_lobby_timeout(chat_id, client))

        await message.reply_text(
            f"🃏 Cᴀʀᴅ Gᴀᴍᴇ Is Hᴇʀᴇ! 🎴\n"
            f"💰 Entry: {money(amount)} each\n"
            f"👥 Players: 1/{required}\n\n"
            f"💡 Others, join with /bet {amount}\n"
            f"⏳ Lobby closes in {LOBBY_SECONDS // 60} minutes if it doesn't fill."
        )

    @app.on_message(filters.group & filters.command("bet"))
    async def bet_cmd(client, message: Message):
        chat_id = message.chat.id
        game = GAMES.get(chat_id)
        if not game or game["phase"] != "lobby":
            return await message.reply_text("⚠️ No open Card Game lobby here — start one with /card <amount> <players>.")

        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text(f"⚠️ Usage: /bet {game['amount']}")

        amount = int(message.command[1])
        if amount != game["amount"]:
            return await message.reply_text(f"⚠️ This lobby's entry is {money(game['amount'])} — use /bet {game['amount']}.")

        user = message.from_user
        if any(p["id"] == user.id for p in game["players"]):
            return await message.reply_text("You're already in this round.")

        if not await take_wager(user.id, user.first_name, amount):
            return await message.reply_text(f"❌ Not enough {CURRENCY_NAME} — you need {money(amount)}.")

        game["players"].append({"id": user.id, "name": user.first_name})
        joined = len(game["players"])

        if joined < game["required"]:
            return await message.reply_text(f"✅ {user.first_name} joined! ({joined}/{game['required']})")

        # Lobby just filled - cancel the refund timer and start the round.
        game["lobby_task"].cancel()
        game["phase"] = "playing"
        hands = deal_hands(joined)
        game["hands"] = {p["id"]: hand for p, hand in zip(game["players"], hands)}
        game["flipped"] = {}
        game["turn_order"] = [p["id"] for p in game["players"]]
        random.shuffle(game["turn_order"])
        game["turn_index"] = 0

        buttons = [
            InlineKeyboardButton(f"👀 {p['name']}", callback_data=f"cardhand:{chat_id}:{p['id']}")
            for p in game["players"]
        ]
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

        await message.reply_text(
            f"✅ {user.first_name} joined! ({joined}/{game['required']})\n\n"
            f"🎴 All players are in — cards dealt!\n"
            f"Everyone's hand sums to the same total, so it's all about which card you reveal.\n"
            f"Tap your name below to privately view your hand.",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        await _announce_turn(chat_id, client, game)

    @app.on_callback_query(filters.regex(r"^cardhand:"))
    async def card_hand_callback(client, callback_query: CallbackQuery):
        _, chat_id_s, uid_s = callback_query.data.split(":")
        chat_id, uid = int(chat_id_s), int(uid_s)

        if callback_query.from_user.id != uid:
            return await callback_query.answer("🚫 This isn't your hand!", show_alert=True)

        game = GAMES.get(chat_id)
        if not game or game.get("phase") != "playing" or uid not in game.get("hands", {}):
            return await callback_query.answer("This round has already ended.", show_alert=True)

        hand = game["hands"][uid]
        flipped_value = game["flipped"].get(uid)
        await callback_query.answer(_hand_view(hand, flipped_value), show_alert=True)

    @app.on_message(filters.group & filters.command("flip"))
    async def flip_cmd(client, message: Message):
        chat_id = message.chat.id
        game = GAMES.get(chat_id)
        if not game or game["phase"] != "playing":
            return await message.reply_text("⚠️ No Card Game in progress here.")

        current_uid = game["turn_order"][game["turn_index"]]
        if message.from_user.id != current_uid:
            return await message.reply_text("⏳ It's not your turn.")

        if len(message.command) < 2 or message.command[1].lower() not in SLOTS:
            return await message.reply_text("⚠️ Usage: /flip a/b/c/d")

        letter = message.command[1].lower()
        idx = SLOTS.index(letter)
        value = game["hands"][current_uid][idx]

        turn_task = game.get("turn_task")
        if turn_task:
            turn_task.cancel()

        await message.reply_text(f"🎴 {message.from_user.first_name} flipped {letter}: **{value}**")
        await _resolve_flip(chat_id, client, current_uid, value)
