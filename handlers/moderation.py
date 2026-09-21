# ============================================================
# 🫧🦋 ʀuɴAk - Moderation
# ============================================================

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions, ChatPrivileges
from pyrogram.errors import RPCError
from pyrogram.enums import MessageEntityType, ChatMemberStatus
import db
from .common import is_admin, resolve_target

# ------------------------------------------------------------
# Promote tiers
# ------------------------------------------------------------
# Three fixed admin ranks, selected with .promote <1|2|3> or
# /promote <1|2|3> (reply to the user, or mention them). Every tier
# explicitly sets is_anonymous=False and can_manage_chat=False -
# there is no way to hand out the "remain anonymous" right, ever.
#
#   1 -> Junior Admin: 3 rights, NO ban, NO add-admin
#   2 -> Senior Admin: 4 rights, incl. ban + add-admin
#   3 -> Head Admin:   5 rights (Senior's 4 + pin messages)
# ------------------------------------------------------------

TIER_PRIVILEGES = {
    1: ChatPrivileges(
        is_anonymous=False,
        can_manage_chat=False,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=False,   
        can_promote_members=False,  
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=True,
    ),
    2: ChatPrivileges(
        is_anonymous=False,
        can_manage_chat=False,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=True,    
        can_promote_members=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
    ),
    3: ChatPrivileges(
        is_anonymous=False,
        can_manage_chat=False,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=True,
        can_promote_members=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=True,
    ),
}

# Custom admin titles shown next to the member's name (Telegram caps these
# at 16 characters - both of these sit right at/under that limit).
TIER_TITLES = {
    1: "➢ 𝗝𝘂ɴɪ𝗼ʀ 𝗮𝗱ᴍɪɴ 𓆪",
    2: "➢ 𝗦𝗲ɴɪ𝗼ʀ 𝗮𝗱ᴍɪɴ 𓆪",
    3: "➢ 𝗛𝗲𝗮ᴅ 𝗮𝗱ᴍɪɴ 𓆪",
}

TIER_LABELS = {1: "Junior Admin", 2: "Senior Admin", 3: "Head Admin"}

# Demoting used to call promote_member(target.id, privileges=None). Pyrogram
# substitutes its own default ChatPrivileges() when privileges is None - and
# that default has can_manage_chat=True. So the "demoted" user quietly stayed
# a (barely visible) admin instead of becoming a normal member again, which
# is why /demote looked like it did nothing. Passing this explicit, fully
# False privileges object strips every right for real, every time.
FULL_DEMOTE_PRIVILEGES = ChatPrivileges(
    is_anonymous=False,
    can_manage_chat=False,
    can_delete_messages=False,
    can_manage_video_chats=False,
    can_restrict_members=False,
    can_promote_members=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
)


def _parse_tier(message: Message):
    """Pull the 1/2/3 tier argument out of the command, wherever it sits."""
    for arg in message.command[1:]:
        if arg in ("1", "2", "3"):
            return int(arg)
    return None


async def _resolve_promote_target(client: Client, message: Message):
    """Like common.resolve_target, but promote-aware: the command args can
    contain a tier number (1/2/3) mixed in with a mention/username, e.g.
    '.promote 2 @username' or '.promote @username 2'. Falls back to a
    reply-to-message target, same as every other moderation command."""
    tier = _parse_tier(message)

    reply = message.reply_to_message
    if reply:
        target = await resolve_target(client, message)
        return target, tier

    for arg in message.command[1:]:
        if arg in ("1", "2", "3"):
            continue
        try:
            return await client.get_users(arg), tier
        except RPCError:
            continue

    if message.entities:
        for entity in message.entities:
            if entity.type == MessageEntityType.TEXT_MENTION and entity.user:
                return entity.user, tier

    return None, tier


def register_moderation_handlers(app: Client):

    @app.on_message(filters.group & filters.command("kick"))
    async def kick_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            await message.chat.ban_member(target.id)
            await message.chat.unban_member(target.id)  # kick = ban + unban
            await message.reply_text(f"👋 {target.first_name} has been kicked.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("ban"))
    async def ban_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            await message.chat.ban_member(target.id)
            await message.reply_text(f"🔨 {target.first_name} has been banned.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("unban"))
    async def unban_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            await message.chat.unban_member(target.id)
            await message.reply_text(f"✅ {target.first_name} has been unbanned.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("mute"))
    async def mute_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            await message.chat.restrict_member(target.id, ChatPermissions())
            await message.reply_text(f"🔇 {target.first_name} has been muted.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("unmute"))
    async def unmute_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            perms = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
            await message.chat.restrict_member(target.id, perms)
            await message.reply_text(f"🔊 {target.first_name} has been unmuted.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("promote", prefixes=["/", "."]))
    async def promote_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")

        target, tier = await _resolve_promote_target(client, message)
        if tier not in TIER_PRIVILEGES:
            return await message.reply_text(
                "⚠️ Usage: reply to a user (or mention them) and pick a tier:\n"
                ".promote 1 — Junior Admin 𓆪 (3 rights, no ban)\n"
                ".promote 2 — Senior Admin 𓆪 (4 rights, ban + add-admin)\n"
                ".promote 3 — Head Admin 𓆪 (5 rights)"
            )
        if not target:
            return await message.reply_text("⚠️ Reply to a user or mention them to promote.")

        try:
            await message.chat.promote_member(target.id, privileges=TIER_PRIVILEGES[tier])
            try:
                await client.set_administrator_title(message.chat.id, target.id, TIER_TITLES[tier])
            except RPCError:
                pass  # custom title is a nice-to-have, don't fail the promotion over it
            await message.reply_text(
                f"⭐ {target.first_name} is now {TIER_LABELS[tier]} {TIER_TITLES[tier]}"
            )
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("demote", prefixes=["/", "."]))
    async def demote_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")

        # Telegram only lets an admin (bot included) demote admins it has
        # rights over - if the bot itself was never given "add new admins"
        # here, promote_member for a demote silently has nothing to do and
        # /demote looks like it "did nothing" instead of erroring. Catch
        # that up front with a clear message instead of a bare retry.
        try:
            me_member = await client.get_chat_member(message.chat.id, "me")
        except RPCError as e:
            return await message.reply_text(f"❌ Couldn't check my own admin rights: {e}")
        if not (me_member.privileges and me_member.privileges.can_promote_members):
            return await message.reply_text(
                "❌ I need the \"Add new admins\" permission myself to demote anyone here."
            )

        try:
            target_member = await client.get_chat_member(message.chat.id, target.id)
        except RPCError as e:
            return await message.reply_text(f"❌ Couldn't check {target.first_name}'s status: {e}")
        if target_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text(f"⚠️ {target.first_name} isn't an admin here.")
        if target_member.status == ChatMemberStatus.OWNER:
            return await message.reply_text("❌ Can't demote the group owner.")

        try:
            await message.chat.promote_member(target.id, privileges=FULL_DEMOTE_PRIVILEGES)
            try:
                await client.set_administrator_title(message.chat.id, target.id, "")
            except RPCError:
                pass

            # Telegram's own state can lag a moment behind the call above -
            # this is the "have to run /demote twice" symptom. Re-check and
            # retry once, in-process, instead of making the admin do it.
            await asyncio.sleep(0.5)
            recheck = await client.get_chat_member(message.chat.id, target.id)
            if recheck.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                await message.chat.promote_member(target.id, privileges=FULL_DEMOTE_PRIVILEGES)
                await asyncio.sleep(0.5)
                recheck = await client.get_chat_member(message.chat.id, target.id)

            if recheck.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                await message.reply_text(
                    f"⚠️ Telegram still shows {target.first_name} as admin after two tries - "
                    "this usually means they were promoted by someone else and I don't have "
                    "rights over them. Try demoting from Telegram's own admin list instead."
                )
            else:
                await message.reply_text(f"⬇️ {target.first_name} has been demoted.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("warn"))
    async def warn_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")

        count = await db.add_warn(message.chat.id, target.id)
        if count >= 3:
            try:
                await message.chat.restrict_member(target.id, ChatPermissions())
                await db.reset_warns(message.chat.id, target.id)
                await message.reply_text(f"🔇 {target.first_name} reached 3 warnings and has been muted.")
            except RPCError as e:
                await message.reply_text(f"❌ Failed to mute after warns: {e}")
        else:
            await message.reply_text(f"⚠️ {target.first_name} has been warned ({count}/3).")

    @app.on_message(filters.group & filters.command("warns"))
    async def warns_cmd(client, message: Message):
        target = await resolve_target(client, message) or message.from_user
        count = await db.get_warns(message.chat.id, target.id)
        await message.reply_text(f"⚠️ {target.first_name} has {count}/3 warnings.")

    @app.on_message(filters.group & filters.command("resetwarns"))
    async def resetwarns_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        await db.reset_warns(message.chat.id, target.id)
        await message.reply_text(f"✅ Warnings cleared for {target.first_name}.")
