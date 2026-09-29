# ============================================================
# 🫧🦋 ʀuɴAk - Fragment Collection Game
# New: Kill and loot users for fragments — collect, merge, and cash them in.
# ============================================================

import time
import random
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import db
from config import CURRENCY_NAME, CURRENCY_EMOJI
from .common import resolve_reply_target

# Fragment Colors & Rarity
FRAGMENT_COLORS = {
    "blue": {"name": "Common", "emoji": "🟦", "value": 10, "next": "purple"},
    "purple": {"name": "Uncommon", "emoji": "🟪", "value": 25, "next": "green"},
    "green": {"name": "Uncommon", "emoji": "🟩", "value": 25, "next": "yellow"},
    "yellow": {"name": "Rare", "emoji": "🟨", "value": 75, "next": "orange"},
    "orange": {"name": "Rare", "emoji": "🟧", "value": 75, "next": "diamond"},
    "diamond": {"name": "Legendary", "emoji": "💎", "value": 250, "next": "emerald"},
    "emerald": {"name": "Legendary", "emoji": "💚", "value": 250, "next": "mythic"},
    "mythic": {"name": "Mythical", "emoji": "⚫", "value": 1000, "next": None},
}

RARITY_WEIGHTS = [
    ("blue", 0.50),
    ("purple", 0.25),
    ("green", 0.10),
    ("yellow", 0.08),
    ("orange", 0.04),
    ("diamond", 0.02),
    ("emerald", 0.008),
    ("mythic", 0.002),
]


async def get_fragments(user_id: int) -> dict:
    """Get user's fragment collection {color: count}"""
    data = await db._get(f"/fragments/{user_id}")
    return data or {}


async def add_fragment(user_id: int, color: str, amount: int = 1):
    """Add fragments to user's collection"""
    frags = await get_fragments(user_id)
    frags[color] = frags.get(color, 0) + amount
    await db._patch(f"/fragments/{user_id}", frags)


async def remove_fragment(user_id: int, color: str, amount: int = 1) -> bool:
    """Remove fragments (returns False if insufficient)"""
    frags = await get_fragments(user_id)
    if frags.get(color, 0) < amount:
        return False
    frags[color] -= amount
    if frags[color] == 0:
        del frags[color]
    await db._patch(f"/fragments/{user_id}", frags or {})
    return True


async def get_fragment_count(user_id: int, color: str) -> int:
    """Get count of a specific fragment color"""
    frags = await get_fragments(user_id)
    return frags.get(color, 0)


def drop_fragment() -> str:
    """Randomly select a fragment color based on rarity weights"""
    rand = random.random()
    cumulative = 0
    for color, weight in RARITY_WEIGHTS:
        cumulative += weight
        if rand <= cumulative:
            return color
    return "blue"


def format_fragments_display(frags: dict) -> str:
    """Format fragment collection for display"""
    if not frags:
        return "📭 You don't have any fragments yet!"
    
    lines = ["🧩 **Your Fragment Collection:**"]
    total_value = 0
    for color, count in sorted(frags.items(), key=lambda x: FRAGMENT_COLORS[x[0]]["value"], reverse=True):
        info = FRAGMENT_COLORS[color]
        value = info["value"] * count
        total_value += value
        lines.append(f"{info['emoji']} {info['name']}: **{count}x** ({value} ₹)")
    
    lines.append(f"\n💰 **Total Value:** {total_value} ₹")
    return "\n".join(lines)


def register_fragment_handlers(app: Client):

    @app.on_message(filters.command("atk"))
    async def atk_cmd(client, message: Message):
        """Attack a user and potentially get fragments"""
        attacker = message.from_user
        victim = await resolve_reply_target(client, message)
        
        if not victim:
            return await message.reply_text("⚠️ Reply to the user you want to attack.")
        
        if victim.id == attacker.id:
            return await message.reply_text("❌ You can't attack yourself.")
        
        await db.add_user(attacker.id, attacker.first_name)
        await db.add_user(victim.id, victim.first_name)
        
        # 60% chance to succeed
        success = random.random() < 0.60
        
        if success:
            # Drop a fragment
            frag_color = drop_fragment()
            await add_fragment(attacker.id, frag_color, 1)
            info = FRAGMENT_COLORS[frag_color]
            
            await message.reply_text(
                f"⚔️ **Attack Successful!**\n"
                f"You hit {victim.first_name} and found:\n"
                f"{info['emoji']} {info['name']} Fragment (+{info['value']} ₹ value)"
            )
        else:
            # Lose some balance
            penalty = random.randint(20, 100)
            await db.add_balance(attacker.id, -penalty)
            await message.reply_text(
                f"🛡️ {victim.first_name} defended themselves!\n"
                f"You lost {penalty} {CURRENCY_EMOJI}."
            )

    @app.on_message(filters.command("loot"))
    async def loot_cmd(client, message: Message):
        """Loot a user and potentially get fragments"""
        looter = message.from_user
        victim = await resolve_reply_target(client, message)
        
        if not victim:
            return await message.reply_text("⚠️ Reply to the user you want to loot.")
        
        if victim.id == looter.id:
            return await message.reply_text("❌ You can't loot yourself.")
        
        await db.add_user(looter.id, looter.first_name)
        await db.add_user(victim.id, victim.first_name)
        
        # 50% chance to succeed
        success = random.random() < 0.50
        
        if success:
            # Drop a fragment
            frag_color = drop_fragment()
            await add_fragment(looter.id, frag_color, 1)
            info = FRAGMENT_COLORS[frag_color]
            
            await message.reply_text(
                f"💰 **Loot Successful!**\n"
                f"You looted {victim.first_name} and found:\n"
                f"{info['emoji']} {info['name']} Fragment (+{info['value']} ₹ value)"
            )
        else:
            penalty = random.randint(30, 80)
            await db.add_balance(looter.id, -penalty)
            await message.reply_text(
                f"🚓 You got caught looting {victim.first_name}!\n"
                f"Fine: {penalty} {CURRENCY_EMOJI}"
            )

    @app.on_message(filters.command("book"))
    async def book_cmd(client, message: Message):
        """View your fragment collection with pagination"""
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        
        frags = await get_fragments(user.id)
        
        if not frags:
            return await message.reply_text("📭 You don't have any fragments yet! Use /atk or /loot.")
        
        text = format_fragments_display(frags)
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="fragment_book_refresh"),
                InlineKeyboardButton("📊 Stats", callback_data="fragment_stats"),
            ],
            [
                InlineKeyboardButton("⬅️ Close", callback_data="fragment_close"),
            ]
        ])
        
        await message.reply_text(text, reply_markup=buttons)

    @app.on_message(filters.command("merge"))
    async def merge_cmd(client, message: Message):
        """Merge 2 fragments of the same color into 1 of the next tier"""
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        
        args = message.command[1:] if len(message.command) > 1 else []
        
        if len(args) < 2:
            colors_list = ", ".join(FRAGMENT_COLORS.keys())
            return await message.reply_text(f"⚠️ Usage: /merge <color> <color>\nColors: {colors_list}")
        
        color1, color2 = args[0].lower(), args[1].lower()
        
        if color1 != color2:
            return await message.reply_text("❌ Both fragments must be the same color!")
        
        if color1 not in FRAGMENT_COLORS:
            return await message.reply_text(f"❌ Unknown color: {color1}")
        
        info = FRAGMENT_COLORS[color1]
        if not info.get("next"):
            return await message.reply_text(f"🎭 {info['emoji']} {info['name']} is the highest tier — can't merge!")
        
        has_enough = await remove_fragment(user.id, color1, 2)
        if not has_enough:
            count = await get_fragment_count(user.id, color1)
            return await message.reply_text(f"❌ You only have {count}x {color1} fragments (need 2)")
        
        next_color = info["next"]
        await add_fragment(user.id, next_color, 1)
        next_info = FRAGMENT_COLORS[next_color]
        
        await message.reply_text(
            f"✨ **Merge Successful!**\n"
            f"2x {info['emoji']} {info['name']} → 1x {next_info['emoji']} {next_info['name']}"
        )

    @app.on_message(filters.command("sell"))
    async def sell_cmd(client, message: Message):
        """Sell fragments for coins or ₹"""
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        
        args = message.command[1:] if len(message.command) > 1 else []
        
        if not args:
            return await message.reply_text("⚠️ Usage: /sell <color> [amount]\nOmit amount to sell all.")
        
        color = args[0].lower()
        amount = int(args[1]) if len(args) > 1 else None
        
        if color not in FRAGMENT_COLORS:
            return await message.reply_text(f"❌ Unknown color: {color}")
        
        frags = await get_fragments(user.id)
        available = frags.get(color, 0)
        
        if available == 0:
            return await message.reply_text(f"❌ You don't have any {color} fragments!")
        
        if amount is None:
            amount = available
        elif amount > available:
            return await message.reply_text(f"❌ You only have {available}x {color} fragments")
        
        info = FRAGMENT_COLORS[color]
        total_value = info["value"] * amount
        
        # Remove fragments
        await remove_fragment(user.id, color, amount)
        
        # Add to funds (for rare+ tiers)
        if color in ["yellow", "orange", "diamond", "emerald", "mythic"]:
            # Add to funds wallet
            funds = await db._get(f"/funds/{user.id}")
            new_funds = (funds or 0) + total_value
            await db._patch(f"/funds/{user.id}", new_funds)
            await message.reply_text(
                f"💎 **Sold {amount}x {info['emoji']} {info['name']}**\n"
                f"Received: +{total_value} ₹ (to your funds wallet)"
            )
        else:
            # Add to regular balance
            await db.add_balance(user.id, total_value)
            await message.reply_text(
                f"💰 **Sold {amount}x {info['emoji']} {info['name']}**\n"
                f"Received: +{total_value} {CURRENCY_EMOJI}"
            )

    @app.on_message(filters.command("funds"))
    async def funds_cmd(client, message: Message):
        """Check your ₹ funds wallet"""
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        
        funds = await db._get(f"/funds/{user.id}") or 0
        
        await message.reply_text(
            f"💼 **Your Funds Wallet**\n\n"
            f"Balance: **{funds} ₹**\n\n"
            f"💡 Sell rare+ fragments to earn ₹\n"
            f"Use ₹ in /shop for premium items"
        )


# Callback handlers for buttons
def register_fragment_callbacks(app: Client):
    
    @app.on_callback_query(filters.regex("fragment_book_refresh"))
    async def refresh_book(client, callback_query):
        user_id = callback_query.from_user.id
        frags = await get_fragments(user_id)
        text = format_fragments_display(frags)
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="fragment_book_refresh"),
                InlineKeyboardButton("📊 Stats", callback_data="fragment_stats"),
            ],
            [
                InlineKeyboardButton("⬅️ Close", callback_data="fragment_close"),
            ]
        ])
        
        await callback_query.edit_message_text(text, reply_markup=buttons)
    
    @app.on_callback_query(filters.regex("fragment_close"))
    async def close_book(client, callback_query):
        await callback_query.delete_message()
