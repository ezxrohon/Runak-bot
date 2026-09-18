# ============================================================
# 🫧🦋 ʀuɴAk - Coupons (owner-issued redeemable codes)
# ============================================================
#
# Owner picks a code + amount with /create_coupon. The coupon is
# single-use overall - whoever redeems it first with /coupon gets
# the reward, then it's locked out for everyone else.
# ============================================================

import re
from pyrogram import Client, filters
from pyrogram.types import Message
import db
from config import CURRENCY_NAME, CURRENCY_EMOJI, OWNER_ID

CODE_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def _is_owner(user_id: int) -> bool:
    return bool(OWNER_ID) and user_id == OWNER_ID


def register_coupon_handlers(app: Client):

    @app.on_message(filters.command("create_coupon"))
    async def create_coupon_cmd(client, message: Message):
        user = message.from_user
        if not _is_owner(user.id):
            return await message.reply_text("❌ Only the bot owner can create coupons.")

        if len(message.command) < 3:
            return await message.reply_text("⚠️ Usage: /create_coupon <code> <amount>")

        code = message.command[1]
        amount_str = message.command[2]

        if not CODE_RE.match(code):
            return await message.reply_text(
                "⚠️ Code must be 3-32 characters: letters, numbers, underscore or hyphen only."
            )

        try:
            amount = int(amount_str)
        except ValueError:
            return await message.reply_text("⚠️ Amount must be a number.")

        if amount <= 0:
            return await message.reply_text("⚠️ Amount must be positive.")

        created = await db.create_coupon(code, amount, user.id)
        if not created:
            return await message.reply_text(f"❌ Coupon `{code}` already exists — pick a different code.")

        await message.reply_text(
            f"🎟️ **Coupon created!**\n"
            f"**Code:** `{code}`\n"
            f"**Value:** {amount} {CURRENCY_EMOJI} {CURRENCY_NAME}\n"
            f"⚠️ One-time use — the first person to redeem it with /coupon {code} gets the reward."
        )

    @app.on_message(filters.command("del_coupon"))
    async def del_coupon_cmd(client, message: Message):
        user = message.from_user
        if not _is_owner(user.id):
            return await message.reply_text("❌ Only the bot owner can delete coupons.")

        await db.delete_all_coupons()
        await message.reply_text("🗑️ All coupons have been deleted.")

    @app.on_message(filters.command("coupon"))
    async def coupon_cmd(client, message: Message):
        user = message.from_user
        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /coupon <code>")

        code = message.command[1]
        await db.add_user(user.id, user.first_name)

        success, amount, reason = await db.redeem_coupon(code, user.id)
        if reason == "not_found":
            return await message.reply_text(f"❌ Coupon `{code}` doesn't exist.")
        if reason == "already_redeemed":
            return await message.reply_text(f"❌ Coupon `{code}` has already been redeemed by someone else.")

        await db.add_balance(user.id, amount)
        await message.reply_text(
            f"✅ {user.first_name} redeemed `{code}` for {amount} {CURRENCY_EMOJI} {CURRENCY_NAME}!"
        )

    @app.on_message(filters.command("status"))
    async def status_cmd(client, message: Message):
        if len(message.command) < 2:
            return await message.reply_text("⚠️ Usage: /status <code>")

        code = message.command[1]
        coupon = await db.get_coupon(code)
        if not coupon:
            return await message.reply_text(f"❌ Coupon `{code}` doesn't exist.")

        if coupon.get("redeemed"):
            await message.reply_text(
                f"🎟️ **Code:** `{code}`\n"
                f"💰 **Value:** {coupon.get('amount', 0)} {CURRENCY_EMOJI}\n"
                f"❌ **Status:** Already redeemed"
            )
        else:
            await message.reply_text(
                f"🎟️ **Code:** `{code}`\n"
                f"💰 **Value:** {coupon.get('amount', 0)} {CURRENCY_EMOJI}\n"
                f"✅ **Status:** Available — first to /coupon {code} wins it"
            )

    @app.on_message(filters.command("coupons"))
    async def coupons_help_cmd(client, message: Message):
        await message.reply_text(
            "🎟️ **Coupon Commands**\n\n"
            f"/coupon <code> — Redeem a coupon\n"
            f"/status <code> — Check a coupon's status\n"
            f"/create_coupon <code> <amount> — Create a coupon (owner only)\n"
            f"/del_coupon — Delete all coupons (owner only)\n"
            f"/coupons — Show this list"
        )
