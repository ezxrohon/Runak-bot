# ============================================================
# 🫧🦋 ʀuɴAk - Shop
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import CURRENCY_EMOJI, CURRENCY_NAME

SHOP_ITEMS = {
    "shield": {"name": "🛡️ Shield", "price": 300, "desc": "Blocks the next /rob attempt against you (cosmetic - track manually)."},
    "vip": {"name": "🌟 VIP Badge", "price": 1000, "desc": "Shows off in your profile flex."},
    "trophy": {"name": "🏆 Trophy", "price": 2000, "desc": "For the richest of the rich."},
    "bubblegum": {"name": "🍬 Bubblegum", "price": 50, "desc": "Just for fun, tastes like Bubbles."},
}


def register_shop_handlers(app: Client):

    @app.on_message(filters.command("shop"))
    async def shop_cmd(client, message: Message):
        lines = [f"🛒 ʀuɴAk Shop ({CURRENCY_NAME})", ""]
        for item_id, item in SHOP_ITEMS.items():
            lines.append(f"{item['name']} — {item['price']} {CURRENCY_EMOJI}  (/buy {item_id})")
            lines.append(f"   {item['desc']}")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.command("buy"))
    async def buy_cmd(client, message: Message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)

        if len(message.command) < 2 or message.command[1].lower() not in SHOP_ITEMS:
            return await message.reply_text("⚠️ Usage: /buy <item_id>. See /shop for the list.")

        item_id = message.command[1].lower()
        item = SHOP_ITEMS[item_id]

        if await db.has_item(user.id, item_id):
            return await message.reply_text(f"You already own {item['name']}.")

        balance = await db.get_balance(user.id)
        if balance < item["price"]:
            return await message.reply_text(f"❌ Not enough {CURRENCY_NAME}. You need {item['price']}, you have {balance}.")

        await db.add_balance(user.id, -item["price"])
        await db.add_item(user.id, item_id)
        await message.reply_text(f"✅ You bought {item['name']}!")

    @app.on_message(filters.command("inventory"))
    async def inventory_cmd(client, message: Message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        inv = await db.get_inventory(user.id)
        if not inv:
            return await message.reply_text("🎒 Your inventory is empty. Try /shop!")

        lines = ["🎒 Your inventory:"]
        for item_id in inv:
            item = SHOP_ITEMS.get(item_id)
            lines.append(f"• {item['name'] if item else item_id}")
        await message.reply_text("\n".join(lines))
