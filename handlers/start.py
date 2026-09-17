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
                    InlineKeyboardButton("⌂ Shop & Gifts ⌂", callback_data="help_shop"),
                    InlineKeyboardButton("⌂ Fun & Games ⌂", callback_data="help_fun"),
                ],
                [
                    InlineKeyboardButton("⌂ Group Tools ⌂", callback_data="help_grouptools"),
                    InlineKeyboardButton("⌂ Notes & Rules ⌂", callback_data="help_notes"),
                ],
                [
                    InlineKeyboardButton("⌂ Utility ⌂", callback_data="help_utility"),
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

    @app.on_message(filters.command("help"))
    async def help_command(client, message):
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
                    InlineKeyboardButton("⌂ Shop & Gifts ⌂", callback_data="help_shop"),
                    InlineKeyboardButton("⌂ Fun & Games ⌂", callback_data="help_fun"),
                ],
                [
                    InlineKeyboardButton("⌂ Group Tools ⌂", callback_data="help_grouptools"),
                    InlineKeyboardButton("⌂ Notes & Rules ⌂", callback_data="help_notes"),
                ],
                [
                    InlineKeyboardButton("⌂ Utility ⌂", callback_data="help_utility"),
                ],
            ]
        )
        await message.reply_text(text, reply_markup=buttons)

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
/balance or /bal — check your Bubbles, rank & status
/daily — claim your daily Bubbles (DM only)
/give <user> <amount> — send Bubbles (10% fee)
/rob (reply) — try to rob someone (risky!)
/leaderboard — richest users
/claim — one-time group reward (100+ members, DM-claimable per group)

⚔️ **PvP**
/kill (reply) — try to kill someone (risky, has a cooldown)
/revive — pay to come back from the dead
/topkill — top 10 by kills
""",
        "help_shop": """
🛍️ Shop & Gifts
─────────────────────────────
/shop — browse cosmetic items for yourself
/buy <item> — buy an item for yourself
/inventory — see what you own
/items — browse the gift catalog
/item (optionally reply) — view a gift inventory
/gift <reply> <item name> — gift an item to a friend
""",
        "help_fun": """
🎉 Fun & Games
─────────────────────────────
/roll — roll a dice
/flip — flip a coin
/8ball <question> — ask the magic 8-ball
/rps <rock|paper|scissors> — play vs the bot
/guess <number> — guess the number (1-100)
/quote — random quote
""",
        "help_grouptools": """
🛡️ Group Tools
─────────────────────────────
/setflood <n> — mute users who send n+ msgs fast
/flood — show current flood limit
/noflood — disable flood protection
/spamban on/off — toggle spam auto-ban
/linkban on/off — toggle link auto-delete
/filter <word> <reply> — add an auto-reply trigger
/filters — list triggers
/stop <word> — remove a trigger
/stopall — remove all triggers
/report (reply) — report a message to admins
/afk <reason> / /brb — mark yourself AFK
""",
        "help_notes": """
📝 Notes & Rules
─────────────────────────────
/save <name> <text> — save a note (#name to trigger)
/get <name> — fetch a note
/notes — list saved notes
/clear <name> — delete a note
/clearall — delete all notes
/setrules <text> — set the group rules
/rules — show the group rules
/clearrules — clear the group rules
""",
        "help_utility": """
🔧 Utility
─────────────────────────────
/id — your ID / chat ID (reply for someone else's)
/info — user info (reply, @username, or id)
/adminlist — list group admins
/chatinfo — info about this chat
/ping — check the bot is alive
/calc <expr> — basic calculator
/time — current time
/echo <text> — repeat text back
/owner — contact the bot owner
""",
    }

    @app.on_callback_query(filters.regex("^help_"))
    async def help_section_callback(client, callback_query):
        text = HELP_TEXTS.get(callback_query.data, "Coming soon.")
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="help")]])
        await callback_query.message.edit_text(text, reply_markup=buttons)
        await callback_query.answer()
