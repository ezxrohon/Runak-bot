# ============================================================
# 🫧🦋 ʀuɴAk - Shop
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import CURRENCY_EMOJI, CURRENCY_NAME
from .common import resolve_target

# Gift items - bought for someone else with /gift, not for yourself.
GIFT_ITEMS = {
    "rose": {"name": "🌹 Rose", "price": 500},
    "chocolate": {"name": "🍫 Chocolate", "price": 800},
    "ring": {"name": "💍 Ring", "price": 2000},
    "teddy bear": {"name": "🧸 Teddy Bear", "price": 1500},
    "pizza": {"name": "🍕 Pizza", "price": 600},
    "surprise box": {"name": "🎁 Surprise Box", "price": 2500},
    "puppy": {"name": "🐶 Puppy", "price": 3000},
    "cake": {"name": "🎂 Cake", "price": 1000},
    "love letter": {"name": "💌 Love Letter", "price": 400},
    "cat": {"name": "🐱 Cat", "price": 2500},
}

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

    # ---- Gift items (send a gift to a friend) ----

    @app.on_message(filters.command("items"))
    async def items_cmd(client, message: Message):
        lines = [f"🎁 Gift Catalog ({CURRENCY_NAME})", ""]
        for item in GIFT_ITEMS.values():
            lines.append(f"{item['name']} — {item['price']} {CURRENCY_EMOJI}")
        lines.append("")
        lines.append("Reply to a friend with /gift <item name> to send one, e.g. /gift rose")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.command("item"))
    async def item_cmd(client, message: Message):
        target = await resolve_target(client, message) or message.from_user
        await db.add_user(target.id, target.first_name)
        gifts = await db.get_gift_inventory(target.id)

        if not gifts:
            who = "Your" if target.id == message.from_user.id else f"{target.first_name}'s"
            return await message.reply_text(f"📦 {who} gift inventory is empty.")

        who = "Your" if target.id == message.from_user.id else f"{target.first_name}'s"
        lines = [f"📦 {who} gift inventory:"]
        for item_id, count in gifts.items():
            item = GIFT_ITEMS.get(item_id)
            name = item["name"] if item else item_id
            lines.append(f"• {name} x{count}")
        await message.reply_text("\n".join(lines))

    @app.on_message(filters.command("gift"))
    async def gift_cmd(client, message: Message):
        sender = message.from_user
        target = await resolve_target(client, message)

        if not target:
            return await message.reply_text("⚠️ Reply to a friend with /gift <item name>, e.g. /gift rose")

        if target.id == sender.id:
            return await message.reply_text("❌ You can't gift yourself.")

        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage (as a reply): /gift <item name>. See /items for the list.")

        item_id = message.text.split(None, 1)[1].strip().lower()
        item = GIFT_ITEMS.get(item_id)
        if not item:
            return await message.reply_text("❌ Unknown item. See /items for the list.")

        await db.add_user(sender.id, sender.first_name)
        await db.add_user(target.id, target.first_name)

        balance = await db.get_balance(sender.id)
        if balance < item["price"]:
            return await message.reply_text(
                f"❌ Not enough {CURRENCY_NAME}. You need {item['price']}, you have {balance}."
            )

        await db.add_balance(sender.id, -item["price"])
        await db.add_gift_item(target.id, item_id)
        await message.reply_text(
            f"🎉 {sender.first_name} gifted {item['name']} to {target.first_name}!"
        )
