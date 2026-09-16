# ============================================================
# 🫧🦋 ʀuɴAk - Moderation
# ============================================================

from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.errors import RPCError
import db


async def resolve_target(client, message: Message):
    """Get the target user from a reply or a mention/username/id argument."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user

    if len(message.command) > 1:
        arg = message.command[1]
        try:
            return await client.get_users(arg)
        except RPCError:
            return None
    return None


async def is_admin(client, chat_id, user_id) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except RPCError:
        return False


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

    @app.on_message(filters.group & filters.command("promote"))
    async def promote_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            await message.chat.promote_member(target.id)
            await message.reply_text(f"⭐ {target.first_name} is now an admin.")
        except RPCError as e:
            await message.reply_text(f"❌ Failed: {e}")

    @app.on_message(filters.group & filters.command("demote"))
    async def demote_cmd(client, message: Message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ You need to be an admin to use this.")
        target = await resolve_target(client, message)
        if not target:
            return await message.reply_text("⚠️ Reply to a user or give a username/id.")
        try:
            await message.chat.promote_member(target.id, privileges=None)
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
