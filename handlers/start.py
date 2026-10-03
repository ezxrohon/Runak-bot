# ============================================================
# 🫧🦋 ʀuɴAk - Start & Help (rich premium UI)
# ============================================================
# /start sends a sticker FIRST, then the colourful premium menu.
# ============================================================

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from config import BOT_USERNAME, BOT_NAME, SUPPORT_GROUP, UPDATE_CHANNEL, START_IMAGE, OWNER_ID, OWNER_USERNAME
import db
from .stickers import pick_start_sticker
from .ui_formatter import bar, esc, help_page

log = logging.getLogger(__name__)
HTML = ParseMode.HTML

STICKER_TIMEOUT = 4  # never keep the user waiting longer than this for the sticker


def start_text(user_name: str) -> str:
    return (
        f"{bar('rainbow')}\n"
        f"✨ <b>Hello {esc(user_name)}!</b> ✨\n"
        f"I am <b>{esc(BOT_NAME)}</b> 🫧🦋\n"
        f"{bar('rainbow')}\n\n"
        "🛡️ <b>Full moderation</b> — kick · ban · mute · warn · locks\n"
        "👋 <b>Welcome messages</b> — your style, your words\n"
        "💰 <b>Bubbles economy</b> — earn · gamble · shop\n"
        "🌟 <b>Levels &amp; XP</b> — climb the ranks\n"
        "🎟️ <b>Coupons</b> — redeem rewards\n"
        "🎮 <b>Games</b> — cards · casino · PvP duels\n"
        "🤖 <b>AI chat</b> — just talk to me\n\n"
        f"{bar('ocean')}\n"
        "👇 <i>Add me to your group to get started!</i>"
    )


def start_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add Me To Your Group ➕", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
            [
                InlineKeyboardButton("🟦 Support", url=SUPPORT_GROUP),
                InlineKeyboardButton("🟩 Updates", url=UPDATE_CHANNEL),
            ],
            [
                InlineKeyboardButton("🟪 Owner", url=f"https://t.me/{OWNER_USERNAME}"),
                InlineKeyboardButton("🟧 Help & Commands", callback_data="help"),
            ],
        ]
    )


HELP_TITLE = (
    f"{bar('rainbow')}\n"
    "📚 <b>HELP MENU</b> 📚\n"
    f"{bar('rainbow')}\n\n"
    "✨ <i>Pick a category below</i> ✨"
)


def help_markup(with_back: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🔴 Moderation", callback_data="help_moderation"),
         InlineKeyboardButton("🟣 Welcome", callback_data="help_welcome")],
        [InlineKeyboardButton("🟠 Locks", callback_data="help_locks"),
         InlineKeyboardButton("🟢 Economy", callback_data="help_economy")],
        [InlineKeyboardButton("🩷 Shop & Gifts", callback_data="help_shop"),
         InlineKeyboardButton("🟡 Fun", callback_data="help_fun")],
        [InlineKeyboardButton("🎮 Games", callback_data="help_games_menu"),
         InlineKeyboardButton("🔵 Levels", callback_data="help_levels")],
        [InlineKeyboardButton("🎟️ Coupons", callback_data="help_coupons"),
         InlineKeyboardButton("🧰 Group Tools", callback_data="help_grouptools")],
        [InlineKeyboardButton("📝 Notes & Rules", callback_data="help_notes"),
         InlineKeyboardButton("🔧 Utility", callback_data="help_utility")],
        [InlineKeyboardButton("👑 Owner Tools", callback_data="help_owner"),
         InlineKeyboardButton("🤖 AI Chat", callback_data="help_ai")],
    ]
    if with_back:
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_start")])
    return InlineKeyboardMarkup(rows)


async def show(client: Client, message, text: str, markup, with_image: bool = False):
    """Edit the menu message in place, whatever kind it currently is.
    A photo message can't have its text edited, so when the target page
    has no image we replace the photo message with a plain text one."""
    has_photo = bool(message.photo)
    if with_image and START_IMAGE:
        if has_photo:
            await message.edit_media(
                InputMediaPhoto(START_IMAGE, caption=text, parse_mode=HTML), reply_markup=markup
            )
        else:
            await message.delete()
            await client.send_photo(
                message.chat.id, START_IMAGE, caption=text, reply_markup=markup, parse_mode=HTML
            )
    elif has_photo:
        await message.delete()
        await client.send_message(message.chat.id, text, reply_markup=markup, parse_mode=HTML)
    else:
        await message.edit_text(text, reply_markup=markup, parse_mode=HTML)


async def send_greeting_sticker(client: Client, message):
    """Send a sticker before the UI. Never raises - if anything goes
    wrong the menu is simply sent without it."""
    try:
        await client.send_chat_action(message.chat.id, ChatAction.CHOOSE_STICKER)
        file_id = await asyncio.wait_for(pick_start_sticker(client), timeout=STICKER_TIMEOUT)
        if file_id:
            await message.reply_sticker(file_id)
            await asyncio.sleep(0.6)  # let the sticker land, then the UI
    except Exception:
        log.warning("Start sticker failed - sending menu without it", exc_info=True)


def register_start_handlers(app: Client):

    @app.on_message(filters.private & filters.command("start"))
    async def start_command(client, message):
        user = message.from_user
        await db.add_user(user.id, user.first_name)

        # 1) sticker first ...
        await send_greeting_sticker(client, message)

        # 2) ... then the premium UI
        text, markup = start_text(user.first_name), start_markup()
        if START_IMAGE:
            await message.reply_photo(START_IMAGE, caption=text, reply_markup=markup, parse_mode=HTML)
        else:
            await message.reply_text(text, reply_markup=markup, parse_mode=HTML)

    @app.on_message(filters.command("help"))
    async def help_command(client, message):
        await message.reply_text(HELP_TITLE, reply_markup=help_markup(with_back=False), parse_mode=HTML)

    @app.on_callback_query(filters.regex("^help$"))
    async def help_callback(client, callback_query):
        await show(client, callback_query.message, HELP_TITLE, help_markup(with_back=True))
        await callback_query.answer()

    @app.on_callback_query(filters.regex("^back_to_start$"))
    async def back_to_start_callback(client, callback_query):
        name = callback_query.from_user.first_name
        await show(client, callback_query.message, start_text(name), start_markup(), with_image=True)
        await callback_query.answer()

    GAMES_TEXT = (
        f"{bar('candy')}\n"
        "🎮 <b>GAMES</b> 🎮\n"
        f"{bar('candy')}\n\n"
        "Wager your Bubbles across three kinds of games.\n"
        "✨ <i>Choose a category</i> ✨"
    )

    async def send_games_menu(client, message):
        buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🃏 Card Game", callback_data="help_cardgame")],
                [InlineKeyboardButton("🎰 Casino Machines", callback_data="help_casino")],
                [InlineKeyboardButton("⚔️ PvP Duels", callback_data="help_duels")],
                [InlineKeyboardButton("🔙 Back", callback_data="help")],
            ]
        )
        await show(client, message, GAMES_TEXT, buttons)

    # Registered before the generic "^help_" handler below, so this exact
    # match is tried first - "help_games_menu" would otherwise also match
    # that handler's "^help_" prefix and fall through to "Coming soon."
    @app.on_callback_query(filters.regex("^help_games_menu$"))
    async def help_games_menu_callback(client, callback_query):
        await send_games_menu(client, callback_query.message)
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
/promote 1 <user> — Junior Admin 𓆪 (3 rights, no ban)
/promote 2 <user> — Senior Admin 𓆪 (4 rights, ban + add-admin)
/promote 3 <user> — Head Admin 𓆪 (5 rights)
/demote <user> — remove admin

.promote / .demote also work. Reply to the user or mention
them, e.g. /ban @username or .promote 2 @username
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
/profile — daily kill/rob quota + wallet at a glance
/daily — claim your daily Bubbles (DM only)
/give <user> <amount> — send Bubbles (10% fee)
/rob (reply only) — try to rob someone (risky!)
/leaderboard or /gleaderboard — richest users (global)
/bleaderboard — richest users (this group)
/claim — one-time group reward (100+ members, DM-claimable per group)

⚔️ **PvP**
/kill (reply only) — try to kill someone (risky, has a cooldown)
/revive — pay to come back from the dead
/topkill or /gbkboard — top 10 by kills (global)
/kleaderboard — top 10 by kills (this group)
""",
        "help_shop": """
🛍️ Shop & Gifts
─────────────────────────────
/shop — browse cosmetic items for yourself
/buy <item> — buy an item for yourself
/inventory — see what you own
/items — browse the gift catalog
/item (optionally reply) — view a gift inventory
/gift <item name> (reply, in group) or /gift <user> <item name> (DM) — gift an item to a friend
""",
        "help_levels": """
🌟 Levels
─────────────────────────────
/level or /lvl (optionally reply) — check level, XP & progress
/toplevel — top 10 XP leaderboard

Earn XP from /daily, successful /rob, and successful /kill.
""",
        "help_coupons": """
🎟️ Coupons
─────────────────────────────
/coupon <code> — redeem a coupon
/status <code> — check a coupon's status
/coupons — show this list

Owner only:
/create_coupon <code> <amount> — create a coupon
/del_coupon — delete all coupons
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

🎟️ Send the bot a sticker (DM) or reply to its message with a
sticker (group) and it'll send one back!
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
/stickerid (reply to a sticker) — get its file_id (optional, only for a manual fallback pool)
""",
        "help_ai": """
🤖 AI Chat
─────────────────────────────
Just talk to me normally — no command needed! I'll reply to any
text message in DM or in a group using AI.

(Owner: requires AI_API_KEY set in .env — see config.py. If unset,
this feature is silently disabled.)
""",
        "help_owner": """
👑 Owner Tools
─────────────────────────────
/broadcast (reply, DM only) — send a message to every bot user
/stats (DM only) — see total registered users

Owner-only — restricted to the bot owner's ID in config.py.
""",
        "help_cardgame": """
🃏  Cᴀʀᴅ Gᴀᴍᴇ Is Hᴇʀᴇ! 🎴
─────────────────────────────
💰 Put your coins on the line
🎯 Choose your card wisely
🏆 Win the pool & take the glory

🎮 Start:
/card <amount> <players>

💡 Join:
/bet <amount>

🎴 Flip:
/flip a/b/c/d

📌 Note:
• Every player gets 4 hidden cards.
• Card sum is the same for everyone.
• Each card can be used only once.
• The highest card revealed wins the pot.
• Game starts once the required players join.
• Lobby time: 2 minutes — unfilled lobbies are refunded in full.
• Each turn has 60 seconds.
""",
        "help_casino": """
🎰 Casino Machines
─────────────────────────────
Wager coins on slots, mines, and roulette.

/jackpot <amount> — animated slot machine (2x-20x payout)
/mines <amount> [mines] — minesweeper-style cashout multiplier
/roulette <amount> <bet> — casino roulette wheel betting

⚠️ Instant payout credited straight to your wallet on a win.
""",
        "help_duels": """
⚔️ Player vs Player Duels
─────────────────────────────
Challenge group members to multiplayer games. Reply to your
opponent's message to challenge them.

/ttt <amount> — Tic-Tac-Toe duel match
/rps <amount> — Rock-Paper-Scissors duel match
(bare /rps rock|paper|scissors still plays solo against me)

⚠️ Draw = 100% refund. Winner takes the pot minus a 5% bank tax.
""",
    }

    # These live one level under "🎮 Games", so their Back button returns
    # to that submenu instead of the main help menu.
    GAMES_SUBPAGES = {"help_cardgame", "help_casino", "help_duels"}

    @app.on_callback_query(filters.regex("^help_"))
    async def help_section_callback(client, callback_query):
        key = callback_query.data
        raw = HELP_TEXTS.get(key)
        text = help_page(key, raw) if raw else "🟨 <b>Coming soon.</b>"
        back_target = "help_games_menu" if key in GAMES_SUBPAGES else "help"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=back_target)]])
        await show(client, callback_query.message, text, buttons)
        await callback_query.answer()
