# ============================================================
# 🫧🦋 ʀuɴAk - Shop
# ============================================================

from pyrogram import Client, filters
from pyrogram.enums import ChatType
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
        lines.append("Group: reply to a friend with /gift <item name>, e.g. /gift rose")
        lines.append("DM: /gift <username> <item name>, e.g. /gift @friend rose")
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

        # Group: /gift <item name> as a reply to the friend's message.
        # DM: no one else's message to reply to, so /gift <username> <item
        # name> instead - the bug was that this branch's item name was
        # never actually separated from the username before being looked
        # up, so it always came back "Unknown item".
        if message.reply_to_message:
            item_words = message.command[1:]
        else:
            item_words = message.command[2:]  # command[1] was the username/id

        if not target:
            return await message.reply_text(
                "⚠️ In a group: reply to a friend with /gift <item name>, e.g. /gift rose\n"
                "In DM: /gift <username> <item name>, e.g. /gift @friend rose"
            )

        if target.id == sender.id:
            return await message.reply_text("❌ You can't gift yourself.")

        if not item_words:
            return await message.reply_text("⚠️ Usage: /gift <item name>. See /items for the list.")

        item_id = " ".join(item_words).strip().lower()
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

        # In DM the recipient isn't in this chat to see that confirmation -
        # message them directly instead. Only works if they've opened a
        # chat with the bot before; Telegram bots can't cold-DM someone
        # who's never started a conversation, so this silently no-ops then.
        if message.chat.type == ChatType.PRIVATE:
            try:
                await client.send_message(
                    target.id,
                    f"🎁 {sender.first_name} gave you a gift: {item['name']}! Check /item to see your gifts."
                )
            except Exception:
                pass
