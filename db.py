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
