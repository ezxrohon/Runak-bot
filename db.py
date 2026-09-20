# ============================================================
# 🫧🦋 ʀuɴAk - Database Layer (Firebase Realtime Database, via REST)
# ============================================================
#
# Firebase's Realtime Database exposes a plain REST API - every path in
# the JSON tree is a URL ending in ".json". No SDK needed, which makes it
# easy to call asynchronously with httpx (fits Pyrogram's asyncio loop).
#
# Tree layout used here:
#   /users/<user_id>          {first_name, balance, bank, inventory, last_daily, last_rob}
#   /welcome/<chat_id>        {message, enabled}
#   /locks/<chat_id>          {locks: {type: bool}}
#   /warns/<chat_id>/<user_id> {count}
# ============================================================

import time
import asyncio
import logging
import httpx
from config import FIREBASE_URL, FIREBASE_SECRET, STARTING_BALANCE

logging.info("✅ Firebase Realtime Database configured")

_client = httpx.AsyncClient(timeout=15)


def _url(path: str) -> str:
    """Build a Firebase REST URL for a given path, e.g. '/users/123'."""
    url = f"{FIREBASE_URL}{path}.json"
    if FIREBASE_SECRET:
        url += f"?auth={FIREBASE_SECRET}"
    return url


async def _get(path: str):
    resp = await _client.get(_url(path))
    resp.raise_for_status()
    return resp.json()


async def _put(path: str, data):
    resp = await _client.put(_url(path), json=data)
    resp.raise_for_status()
    return resp.json()


async def _patch(path: str, data: dict):
    resp = await _client.patch(_url(path), json=data)
    resp.raise_for_status()
    return resp.json()


async def _delete(path: str):
    resp = await _client.delete(_url(path))
    resp.raise_for_status()


# ==========================================================
# 👤 Users (global profile, used across all groups)
# ==========================================================

async def add_user(user_id, first_name):
    existing = await _get(f"/users/{user_id}")
    if existing:
        await _patch(f"/users/{user_id}", {"first_name": first_name})
    else:
        await _put(
            f"/users/{user_id}",
            {
                "first_name": first_name,
                "balance": STARTING_BALANCE,
                "bank": 0,
                "inventory": [],
                "last_daily": 0,
                "last_rob": 0,
                "kills": 0,
                "status": "alive",
                "xp": 0,
            },
        )


def _as_dict(data):
    """Firebase returns a JSON array instead of an object if all keys happen
    to be sequential integers from 0 - normalize back to a dict either way."""
    if isinstance(data, list):
        return {str(i): v for i, v in enumerate(data) if v is not None}
    return data or {}


async def get_all_users():
    data = _as_dict(await _get("/users"))
    return [int(uid) for uid in data.keys()]


async def get_user(user_id):
    user = await _get(f"/users/{user_id}")
    if not user:
        await add_user(user_id, "Unknown")
        user = await _get(f"/users/{user_id}")
    return user


# ==========================================================
# 💰 Economy
# ==========================================================

async def get_balance(user_id) -> int:
    user = await get_user(user_id)
    return user.get("balance", 0)


async def add_balance(user_id, amount: int):
    user = await get_user(user_id)
    new_balance = user.get("balance", 0) + amount
    await _patch(f"/users/{user_id}", {"balance": new_balance})


async def set_balance(user_id, amount: int):
    await _patch(f"/users/{user_id}", {"balance": amount})


async def transfer_balance(from_id, to_id, amount: int) -> bool:
    sender = await get_user(from_id)
    if sender.get("balance", 0) < amount:
        return False
    await add_balance(from_id, -amount)
    await add_balance(to_id, amount)
    return True


async def get_leaderboard(limit: int = 10):
    data = _as_dict(await _get("/users"))
    entries = []
    for uid, info in data.items():
        entries.append({"user_id": int(uid), "first_name": info.get("first_name", "Unknown"), "balance": info.get("balance", 0)})
    entries.sort(key=lambda e: e["balance"], reverse=True)
    return entries[:limit]


# ---- Per-chat membership tracking (lightweight - just enough to scope
# leaderboards to a single group; see handlers/tracking.py, which records
# every user who sends a message in a group) ----

async def record_chat_member(chat_id, user_id):
    await _patch(f"/chat_members/{chat_id}", {str(user_id): True})


async def get_chat_member_ids(chat_id) -> list:
    data = _as_dict(await _get(f"/chat_members/{chat_id}"))
    return [int(uid) for uid in data.keys()]


async def get_group_leaderboard(chat_id, limit: int = 10):
    """Balance leaderboard scoped to users we've seen active in this chat."""
    member_ids = await get_chat_member_ids(chat_id)
    if not member_ids:
        return []
    users = await asyncio.gather(*(get_user(uid) for uid in member_ids))
    entries = [
        {"user_id": uid, "first_name": u.get("first_name", "Unknown"), "balance": u.get("balance", 0)}
        for uid, u in zip(member_ids, users)
    ]
    entries.sort(key=lambda e: e["balance"], reverse=True)
    return entries[:limit]


async def get_group_kill_leaderboard(chat_id, limit: int = 10):
    """Kill leaderboard scoped to users we've seen active in this chat."""
    member_ids = await get_chat_member_ids(chat_id)
    if not member_ids:
        return []
    users = await asyncio.gather(*(get_user(uid) for uid in member_ids))
    entries = [
        {"user_id": uid, "first_name": u.get("first_name", "Unknown"), "kills": u.get("kills", 0)}
        for uid, u in zip(member_ids, users)
    ]
    entries.sort(key=lambda e: e["kills"], reverse=True)
    return entries[:limit]


async def get_rank(user_id) -> int:
    """1-based global rank by balance (highest balance = rank 1)."""
    data = _as_dict(await _get("/users"))
    balances = sorted((info.get("balance", 0) for info in data.values()), reverse=True)
    user = await get_user(user_id)
    my_balance = user.get("balance", 0)
    try:
        return balances.index(my_balance) + 1
    except ValueError:
        return len(balances) + 1


# ---- XP / Levels ----

async def get_xp(user_id) -> int:
    user = await get_user(user_id)
    return user.get("xp", 0)


async def add_xp(user_id, amount: int) -> int:
    """Add (or subtract) XP and return the new total. Never goes below 0."""
    user = await get_user(user_id)
    new_xp = max(0, user.get("xp", 0) + amount)
    await _patch(f"/users/{user_id}", {"xp": new_xp})
    return new_xp


async def get_xp_leaderboard(limit: int = 10):
    data = _as_dict(await _get("/users"))
    entries = []
    for uid, info in data.items():
        entries.append({"user_id": int(uid), "first_name": info.get("first_name", "Unknown"), "xp": info.get("xp", 0)})
    entries.sort(key=lambda e: e["xp"], reverse=True)
    return entries[:limit]


# ---- Kills / status (placeholders for a future PvP system) ----

async def get_kills(user_id) -> int:
    user = await get_user(user_id)
    return user.get("kills", 0)


async def add_kill(user_id, amount: int = 1):
    user = await get_user(user_id)
    await _patch(f"/users/{user_id}", {"kills": user.get("kills", 0) + amount})


async def get_kill_leaderboard(limit: int = 10):
    data = _as_dict(await _get("/users"))
    entries = []
    for uid, info in data.items():
        entries.append({"user_id": int(uid), "first_name": info.get("first_name", "Unknown"), "kills": info.get("kills", 0)})
    entries.sort(key=lambda e: e["kills"], reverse=True)
    return entries[:limit]


async def get_status(user_id) -> str:
    user = await get_user(user_id)
    return user.get("status", "alive")


async def set_status(user_id, status: str):
    await _patch(f"/users/{user_id}", {"status": status})


# ---- Kill cooldown ----

async def get_last_kill(user_id) -> float:
    user = await get_user(user_id)
    return user.get("last_kill", 0)


async def set_last_kill(user_id):
    await _patch(f"/users/{user_id}", {"last_kill": time.time()})


# ---- Daily kill quota (shown on /profile, resets 24h after the first
# kill attempt of the "day" - rolling window, not calendar-day-aligned) ----

async def get_daily_kills(user_id) -> int:
    user = await get_user(user_id)
    if time.time() >= user.get("daily_kills_reset", 0):
        return 0
    return user.get("daily_kills", 0)


async def bump_daily_kills(user_id) -> int:
    """Increments today's /kill attempt counter and returns the new total."""
    user = await get_user(user_id)
    now = time.time()
    reset_at = user.get("daily_kills_reset", 0)
    count = user.get("daily_kills", 0)
    if now >= reset_at:
        count = 0
        reset_at = now + 24 * 60 * 60
    count += 1
    await _patch(f"/users/{user_id}", {"daily_kills": count, "daily_kills_reset": reset_at})
    return count


# ---- Protection window (blocks /rob and /kill against this user) ----

async def get_protection_until(user_id) -> float:
    user = await get_user(user_id)
    return user.get("protection_until", 0)


async def set_protection(user_id, hours: float):
    await _patch(f"/users/{user_id}", {"protection_until": time.time() + hours * 3600})


async def clear_protection(user_id):
    await _patch(f"/users/{user_id}", {"protection_until": 0})


async def get_protection_remaining(user_id) -> float:
    """Seconds of protection left, 0 if not protected."""
    until = await get_protection_until(user_id)
    remaining = until - time.time()
    return remaining if remaining > 0 else 0


# ---- Per-group one-time /claim reward ----

async def has_claimed_group(chat_id) -> bool:
    data = await _get(f"/claims/{chat_id}")
    return bool(data and data.get("claimed"))


async def set_claimed_group(chat_id, user_id):
    await _put(f"/claims/{chat_id}", {"claimed": True, "claimed_by": user_id, "at": time.time()})


# ---- Daily reward ----

async def get_last_daily(user_id) -> float:
    user = await get_user(user_id)
    return user.get("last_daily", 0)


async def set_last_daily(user_id):
    await _patch(f"/users/{user_id}", {"last_daily": time.time()})


# ---- Rob cooldown ----

async def get_last_rob(user_id) -> float:
    user = await get_user(user_id)
    return user.get("last_rob", 0)


async def set_last_rob(user_id):
    await _patch(f"/users/{user_id}", {"last_rob": time.time()})


# ---- Daily rob quota (shown on /profile, same rolling-24h reset as kills) ----

async def get_daily_robs(user_id) -> int:
    user = await get_user(user_id)
    if time.time() >= user.get("daily_robs_reset", 0):
        return 0
    return user.get("daily_robs", 0)


async def bump_daily_robs(user_id) -> int:
    """Increments today's /rob attempt counter and returns the new total."""
    user = await get_user(user_id)
    now = time.time()
    reset_at = user.get("daily_robs_reset", 0)
    count = user.get("daily_robs", 0)
    if now >= reset_at:
        count = 0
        reset_at = now + 24 * 60 * 60
    count += 1
    await _patch(f"/users/{user_id}", {"daily_robs": count, "daily_robs_reset": reset_at})
    return count


# ---- Inventory / Shop ----

async def get_inventory(user_id):
    user = await get_user(user_id)
    return user.get("inventory", []) or []


async def add_item(user_id, item_id: str):
    inv = await get_inventory(user_id)
    inv.append(item_id)
    await _patch(f"/users/{user_id}", {"inventory": inv})


async def has_item(user_id, item_id: str) -> bool:
    inv = await get_inventory(user_id)
    return item_id in inv


async def remove_item(user_id, item_id: str):
    inv = await get_inventory(user_id)
    if item_id in inv:
        inv.remove(item_id)
        await _patch(f"/users/{user_id}", {"inventory": inv})


# ---- Gifted items (separate from the self-buy shop, allows duplicates) ----

async def get_gift_inventory(user_id) -> dict:
    """Returns {item_id: count} of gift items this user has received."""
    data = await _get(f"/gifts/{user_id}")
    return data or {}


async def add_gift_item(user_id, item_id: str, amount: int = 1):
    inv = await get_gift_inventory(user_id)
    inv[item_id] = inv.get(item_id, 0) + amount
    await _patch(f"/gifts/{user_id}", {item_id: inv[item_id]})


# ==========================================================
# 🎟️ Coupons
# ==========================================================

async def create_coupon(code: str, amount: int, created_by: int) -> bool:
    """Create a coupon if the code isn't already taken. Returns False if it exists."""
    existing = await _get(f"/coupons/{code}")
    if existing:
        return False
    await _put(
        f"/coupons/{code}",
        {
            "amount": amount,
            "created_by": created_by,
            "created_at": time.time(),
            "redeemed": False,
            "redeemed_by": None,
            "redeemed_at": 0,
        },
    )
    return True


async def get_coupon(code: str):
    return await _get(f"/coupons/{code}")


async def redeem_coupon(code: str, user_id: int):
    """Redeem a coupon (first-come-first-served, single use overall).
    Returns (success: bool, amount: int|None, reason: str)."""
    coupon = await get_coupon(code)
    if not coupon:
        return False, None, "not_found"
    if coupon.get("redeemed"):
        return False, None, "already_redeemed"

    await _patch(
        f"/coupons/{code}",
        {"redeemed": True, "redeemed_by": user_id, "redeemed_at": time.time()},
    )
    return True, coupon.get("amount", 0), "ok"


async def delete_all_coupons():
    await _delete("/coupons")


# ==========================================================
# 🟢 Welcome
# ==========================================================

async def set_welcome_message(chat_id, text: str):
    await _patch(f"/welcome/{chat_id}", {"message": text})


async def get_welcome_message(chat_id):
    data = await _get(f"/welcome/{chat_id}")
    return data.get("message") if data else None


async def set_welcome_status(chat_id, status: bool):
    await _patch(f"/welcome/{chat_id}", {"enabled": status})


async def get_welcome_status(chat_id) -> bool:
    data = await _get(f"/welcome/{chat_id}")
    return bool(data.get("enabled", True)) if data else True


# ==========================================================
# 🔒 Locks
# ==========================================================

async def set_lock(chat_id, lock_type, status: bool):
    await _patch(f"/locks/{chat_id}/locks", {lock_type: status})


async def get_locks(chat_id):
    data = await _get(f"/locks/{chat_id}")
    return (data or {}).get("locks", {}) or {}


# ==========================================================
# ⚠️ Warn
# ==========================================================

async def add_warn(chat_id: int, user_id: int) -> int:
    data = await _get(f"/warns/{chat_id}/{user_id}")
    warns = (data.get("count", 0) if data else 0) + 1
    await _put(f"/warns/{chat_id}/{user_id}", {"count": warns})
    return warns


async def get_warns(chat_id: int, user_id: int) -> int:
    data = await _get(f"/warns/{chat_id}/{user_id}")
    return data.get("count", 0) if data else 0


async def reset_warns(chat_id: int, user_id: int):
    await _put(f"/warns/{chat_id}/{user_id}", {"count": 0})


# ==========================================================
# 🧹 Cleanup
# ==========================================================

async def clear_group_data(chat_id: int):
    await _delete(f"/welcome/{chat_id}")
    await _delete(f"/locks/{chat_id}")
    await _delete(f"/warns/{chat_id}")
    await _delete(f"/flood/{chat_id}")
    await _delete(f"/spamban/{chat_id}")
    await _delete(f"/linkban/{chat_id}")
    await _delete(f"/filters/{chat_id}")
    await _delete(f"/notes/{chat_id}")
    await _delete(f"/rules/{chat_id}")


# ==========================================================
# 😴 AFK (global, per-user - not tied to a specific chat)
# ==========================================================

async def set_afk(user_id, reason: str):
    await _put(f"/afk/{user_id}", {"reason": reason, "since": time.time()})


async def get_afk(user_id):
    """Returns {'reason': ..., 'since': ...} if the user is AFK, else None."""
    return await _get(f"/afk/{user_id}")


async def clear_afk(user_id):
    await _delete(f"/afk/{user_id}")


# ==========================================================
# 🌊 Anti-flood (per-chat message-rate limit)
# ==========================================================

async def set_flood_limit(chat_id, limit):
    """limit=None (or any non-positive value) disables flood protection."""
    if limit and limit > 0:
        await _put(f"/flood/{chat_id}", {"limit": limit})
    else:
        await _delete(f"/flood/{chat_id}")


async def get_flood_limit(chat_id):
    """Returns the limit as an int, or None if flood protection is off."""
    data = await _get(f"/flood/{chat_id}")
    if not data:
        return None
    limit = data.get("limit")
    return limit if limit and limit > 0 else None


# ==========================================================
# 🛡️ Spam ban (per-chat on/off toggle)
# ==========================================================

async def set_spamban(chat_id, enabled: bool):
    await _patch(f"/spamban/{chat_id}", {"enabled": enabled})


async def get_spamban(chat_id) -> bool:
    data = await _get(f"/spamban/{chat_id}")
    return bool(data.get("enabled")) if data else False


# ==========================================================
# 🔗 Link ban (per-chat on/off toggle)
# ==========================================================

async def set_linkban(chat_id, enabled: bool):
    await _patch(f"/linkban/{chat_id}", {"enabled": enabled})


async def get_linkban(chat_id) -> bool:
    data = await _get(f"/linkban/{chat_id}")
    return bool(data.get("enabled")) if data else False


# ==========================================================
# 🔍 Filters (per-chat trigger word -> reply text)
# ==========================================================

async def add_filter(chat_id, word: str, reply: str):
    await _patch(f"/filters/{chat_id}", {word: reply})


async def get_all_filters(chat_id) -> dict:
    data = await _get(f"/filters/{chat_id}")
    return data or {}


async def delete_filter(chat_id, word: str):
    await _delete(f"/filters/{chat_id}/{word}")


async def clear_all_filters(chat_id):
    await _delete(f"/filters/{chat_id}")


# ==========================================================
# 📝 Notes (per-chat name -> text)
# ==========================================================

async def save_note(chat_id, name: str, text: str):
    await _patch(f"/notes/{chat_id}", {name: text})


async def get_note(chat_id, name: str):
    data = await _get(f"/notes/{chat_id}")
    return (data or {}).get(name)


async def get_all_notes(chat_id) -> dict:
    data = await _get(f"/notes/{chat_id}")
    return data or {}


async def delete_note(chat_id, name: str):
    await _delete(f"/notes/{chat_id}/{name}")


async def clear_all_notes(chat_id):
    await _delete(f"/notes/{chat_id}")


# ==========================================================
# 📜 Rules (per-chat text blob)
# ==========================================================

async def set_rules(chat_id, text: str):
    await _patch(f"/rules/{chat_id}", {"text": text})


async def get_rules(chat_id):
    data = await _get(f"/rules/{chat_id}")
    return data.get("text") if data else None


async def clear_rules(chat_id):
    await _delete(f"/rules/{chat_id}")
