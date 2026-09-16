# ============================================================
# 🫧🦋 ʀuɴAk - Start & Help
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from config import BOT_USERNAME, BOT_NAME, SUPPORT_GROUP, UPDATE_CHANNEL, START_IMAGE, OWNER_ID, OWNER_USERNAME
import db


def register_start_handlers(app: Client):

    async def send_start_menu(message, user_name):
        text = f"""
✨ Hello {user_name}! ✨

I am {BOT_NAME} 🫧🦋

A group manager with a fun side:
─────────────────────────────
• Full moderation (kick / ban / mute / warn / locks)
• Welcome messages
• Bubbles economy (earn, gamble, shop)
• Games & fun commands

» Add me to your group to get started!
"""
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚒️ Add to Group ⚒️", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
                [
                    InlineKeyboardButton("⌂ Support ⌂", url=SUPPORT_GROUP),
                    InlineKeyboardButton("⌂ Updates ⌂", url=UPDATE_CHANNEL),
                ],
                [InlineKeyboardButton("※ Owner ※", url=f"https://t.me/{OWNER_USERNAME}")],
                [InlineKeyboardButton("📚 Help Commands 📚", callback_data="help")],
            ]
        )

        if START_IMAGE:
            if message.text:
                await message.reply_photo(START_IMAGE, caption=text, reply_markup=buttons)
            else:
                media = InputMediaPhoto(media=START_IMAGE, caption=text)
                await message.edit_media(media=media, reply_markup=buttons)
        else:
            if message.text:
                await message.reply_text(text, reply_markup=buttons)
            else:
                await message.edit_text(text, reply_markup=buttons)

    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client, message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)
        await send_start_menu(message, user.first_name)

    async def send_help_menu(message):
        text = """
╔══════════════════╗
     Help Menu
╚══════════════════╝

Choose a category:
"""
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⌂ Moderation ⌂", callback_data="help_moderation"),
                    InlineKeyboardButton("⌂ Welcome ⌂", callback_data="help_welcome"),
                ],
                [
                    InlineKeyboardButton("⌂ Locks ⌂", callback_data="help_locks"),
                    InlineKeyboardButton("⌂ Economy ⌂", callback_data="help_economy"),
                ],
                [
                    InlineKeyboardButton("⌂ Fun & Games ⌂", callback_data="help_fun"),
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")],
            ]
        )
        if message.photo or (message.caption is not None):
            media = InputMediaPhoto(media=START_IMAGE, caption=text) if START_IMAGE else None
            if media:
                await message.edit_media(media=media, reply_markup=buttons)
                return
        await message.edit_text(text, reply_markup=buttons)

    @app.on_callback_query(filters.regex("^help$"))
    async def help_callback(client, callback_query):
        await send_help_menu(callback_query.message)
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^back_to_start$"))
    async def back_to_start_callback(client, callback_query):
        user_name = callback_query.from_user.first_name
        await send_start_menu(callback_query.message, user_name)
        await callback_query.answer()

    HELP_TEXTS = {
        "help_moderation": """
⚙️ Moderation
─────────────────────────────
/kick <user> — remove a user
/ban <user> — ban permanently
/unban <user> — lift a ban
/mute <user> — silence a user
/unmute <user> — allow messages again
/warn <user> — add a warning (3 = auto-mute)
/warns <user> — view warning count
/resetwarns <user> — clear warnings
/promote <user> — make admin
/demote <user> — remove admin

Reply to the user or mention them, e.g. /ban @username
""",
        "help_welcome": """
⚙️ Welcome System
─────────────────────────────
/setwelcome <text> — set a custom welcome message
/welcome on / off — toggle welcome messages

Placeholders: {first_name} {mention} {id} {title}
""",
        "help_locks": """
⚙️ Locks
─────────────────────────────
/lock <type> — block a message type
/unlock <type> — allow it again
/locks — show active locks

Types: url, sticker, media, username, forward
""",
        "help_economy": """
💰 Economy
─────────────────────────────
/balance — check your Bubbles
/daily — claim your daily Bubbles
/give <user> <amount> — send Bubbles to someone
/rob <user> — try to rob someone (risky!)
/leaderboard — richest users
/shop — browse the shop
/buy <item> — buy an item
/inventory — see what you own
""",
        "help_fun": """
🎉 Fun & Games
─────────────────────────────
/roll — roll a dice
/flip — flip a coin
/8ball <question> — ask the magic 8-ball
/rps <rock|paper|scissors> — play vs the bot
/guess <number> — guess the number (1-100)
/hug /slap /pat <user> — react at someone
/quote — random quote
""",
    }

    @app.on_callback_query(filters.regex("^help_"))
    async def help_section_callback(client, callback_query):
        text = HELP_TEXTS.get(callback_query.data, "Coming soon.")
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_text(text, reply_markup=buttons)
        await callback_query.answer()
