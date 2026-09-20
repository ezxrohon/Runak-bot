# ============================================================
# 🫧🦋 ʀuɴAk - Shared game-economy helpers
# ============================================================
#
# Used by cardgame.py, casino.py and duels.py - every wager-based game
# goes through the same take/refund/payout path so balance bugs (double
# spends, lost stakes on crash, etc.) only have to be gotten right once.
#
# All game state below (lobbies, boards, in-progress rounds) lives in
# plain in-memory dicts, not the database - these games are short-lived
# and resetting on a bot restart is an acceptable trade-off for not
# hammering Firebase every second during a live round. Money itself
# (the actual wagers) is always the real, persisted balance in db.py.
# ============================================================

import db
from config import CURRENCY_EMOJI, CURRENCY_NAME, BANK_TAX


async def take_wager(user_id, first_name, amount: int) -> bool:
    """Deduct `amount` from the user's balance if they can afford it.
    Returns True/False - never raises. Call refund_wager to reverse."""
    await db.add_user(user_id, first_name)
    balance = await db.get_balance(user_id)
    if balance < amount:
        return False
    await db.add_balance(user_id, -amount)
    return True


async def refund_wager(user_id, amount: int):
    """Give a wager back - used when a lobby doesn't fill, or on a draw."""
    if amount:
        await db.add_balance(user_id, amount)


async def payout(user_id, amount: int):
    """Credit a win straight to the wallet - instant, no claim step."""
    if amount:
        await db.add_balance(user_id, amount)


def pot_after_tax(pot: int) -> int:
    """PvP duel payout: pot minus the house's 5% cut."""
    return int(pot * (1 - BANK_TAX))


def money(amount: int) -> str:
    return f"{amount} {CURRENCY_EMOJI} {CURRENCY_NAME}"
