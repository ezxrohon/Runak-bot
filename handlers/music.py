# ============================================================
# 🫧🦋 ʀuɴAk - Music (voice chat)
# ============================================================
#
# Bots can't join a Telegram voice chat by themselves - only user
# accounts can. So this feature runs a second Telegram client (the
# "assistant") logged in with SESSION_STRING, and streams audio into
# the group's voice chat through it via PyTgCalls. The bot itself just
# handles the commands.
#
# Completely inactive (nothing imported, no handlers registered, no
# extra client created) if SESSION_STRING isn't set in .env - so the
# rest of the bot works fine without ever installing py-tgcalls /
# yt-dlp / py-yt-search if you don't want voice-chat music at all.
#
# NOTE: pytgcalls' exact API (MediaStream / AudioQuality / VideoQuality
# / StreamEnded / calls.play / calls.change_stream ...) can shift
# slightly between minor versions. This targets py-tgcalls 2.x - if a
# call doesn't match your installed version, check that package's
# changelog.
#
# Also needs the `ffmpeg` binary on the machine running the bot (for
# both yt-dlp and pytgcalls). Render's default Python runtime does NOT
# include it - see the Dockerfile added alongside this feature.
# ============================================================

import logging
import time

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

import config
from . import music_utils as music
from .common import is_admin

log = logging.getLogger(__name__)

MUSIC_ENABLED = config.MUSIC_ENABLED

# These stay None (and every handler below is simply never registered)
# unless SESSION_STRING is configured.
userbot: Client | None = None
calls = None

if MUSIC_ENABLED:
    userbot = Client(
        "runak_assistant",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.SESSION_STRING,
    )
    try:
        from pytgcalls import PyTgCalls
        from pytgcalls.types import AudioQuality, MediaStream, Update, VideoQuality
        from pytgcalls.types.stream import StreamEnded

        calls = PyTgCalls(userbot)
    except ImportError:
        log.warning(
            "SESSION_STRING is set but py-tgcalls isn't installed - "
            "run `pip install -r requirements.txt` to enable music. "
            "Music feature disabled for this run."
        )
        MUSIC_ENABLED = False
        userbot = None
        calls = None

# In-memory playback state: chat_id -> [...]. Fine for a single-process
# bot; if you ever run more than one worker, this needs to move to a
# shared store instead.
QUEUES: dict = {}
CURRENT: dict = {}
LOOPS: dict = {}


def _player_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸", callback_data="music_pause"),
                InlineKeyboardButton("▶️", callback_data="music_resume"),
                InlineKeyboardButton("⏭", callback_data="music_skip"),
                InlineKeyboardButton("⏹", callback_data="music_stop"),
            ]
        ]
    )


def _stream(file: str, video: bool, seek_seconds: int = 0):
    return MediaStream(
        file,
        audio_parameters=AudioQuality.STUDIO,
        video_parameters=VideoQuality.SD_480p if video else None,
        ffmpeg_parameters=f"-ss {seek_seconds}" if seek_seconds else None,
    )


async def _join_and_play(chat_id: int, track: dict, video: bool) -> None:
    await calls.play(chat_id, _stream(track["file"], video))
    CURRENT[chat_id] = {**track, "video": video, "started": time.time(), "offset": 0}


async def _change_to(chat_id: int, track: dict, video: bool, seek_seconds: int = 0) -> None:
    await calls.change_stream(chat_id, _stream(track["file"], video, seek_seconds))
    CURRENT[chat_id] = {**track, "video": video, "started": time.time(), "offset": seek_seconds}


async def _leave(chat_id: int) -> None:
    try:
        await calls.leave_call(chat_id)
    except Exception:
        pass


async def play_next(chat_id: int) -> dict | None:
    """Advance to the next queued track, or leave the call if empty."""
    queue = QUEUES.get(chat_id, [])
    if queue:
        track = queue.pop(0)
        await _change_to(chat_id, track, track.get("video", False))
        return track
    await _leave(chat_id)
    CURRENT.pop(chat_id, None)
    return None


def _elapsed(chat_id: int) -> int:
    track = CURRENT.get(chat_id)
    if not track:
        return 0
    return int(track["offset"] + (time.time() - track["started"]))


async def _seek_to(chat_id: int, position: int) -> None:
    track = CURRENT[chat_id]
    position = max(0, position)
    await _change_to(chat_id, track, track.get("video", False), seek_seconds=position)


def _fmt_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


async def _require_vc_admin(client, message: Message) -> bool:
    """Playback controls (skip/stop/pause/etc) are admin-only so randoms
    in the group can't hijack the queue - /play itself stays open to
    everyone. Returns True and does nothing if the check passes; replies
    and returns False if it doesn't."""
    if await is_admin(client, message.chat.id, message.from_user.id):
        return True
    await message.reply_text("❌ Only group admins can control playback.")
    return False


async def _ensure_assistant_in_chat(client, message: Message) -> str | None:
    """Makes sure the assistant account is actually a member of this chat
    before trying to join its voice chat - it can't stream into a VC it
    isn't even in. If it's missing, the bot (which is already in the
    group) mints a fresh invite link and the assistant joins through it
    automatically, so nobody has to add it by hand.

    Returns None on success, or a user-facing error string on failure.
    """
    chat_id = message.chat.id
    try:
        await userbot.get_chat_member(chat_id, "me")
        return None  # already in the chat, nothing to do
    except Exception:
        pass  # not in the chat (or unresolved yet) - try to bring it in

    try:
        link = await client.export_chat_invite_link(chat_id)
    except Exception as e:
        return (
            "❌ The assistant account isn't in this group yet, and I couldn't "
            f"create an invite link to add it myself ({e}).\n\n"
            "Give me the \"Invite users via link\" admin permission and try "
            "again, or add the assistant account to this group manually."
        )

    try:
        await userbot.join_chat(link)
    except Exception as e:
        return (
            "❌ The assistant account isn't in this group and couldn't join "
            f"automatically ({e}).\n\n"
            f"Please add it manually using this invite link: {link}"
        )

    log.info("Assistant auto-joined chat %s to play music.", chat_id)
    return None


def _now_playing_caption(action: str, track: dict, requester: str, chat_id: int | None = None) -> str:
    duration = track.get("duration") or "?"
    caption = f"{action} {track['title']}\n⏱ Duration: {duration}\n🎧 Requested by: {requester}"
    if chat_id is not None:
        queue_len = len(QUEUES.get(chat_id, []))
        if queue_len:
            caption += f"\n📃 {queue_len} track(s) queued"
    return caption


async def _send_now_playing(status: Message, track: dict, caption: str, buttons=None) -> None:
    """Shows the now-playing/queued card. Uses the track's YouTube
    thumbnail when we have one (converting the plain 'Searching...' text
    message into a photo message), falling back to a plain text edit if
    the thumbnail is missing or Telegram rejects the image URL for any
    reason - playback itself still works either way."""
    thumbnail = track.get("thumbnail")
    if thumbnail:
        try:
            await status.edit_media(
                InputMediaPhoto(thumbnail, caption=caption),
                reply_markup=buttons,
            )
            return
        except Exception:
            log.info("Couldn't attach thumbnail for %r, falling back to text.", track.get("title"))
    await status.edit_text(caption, reply_markup=buttons)


def register_music_handlers(app: Client):
    if not MUSIC_ENABLED:
        log.info(
            "Music feature disabled - set SESSION_STRING in .env to enable "
            "voice-chat music (see config.py for how to generate one)."
        )
        return

    # ---------------------------------------------------------- playback

    async def _play(client, message: Message, video: bool, force: bool) -> None:
        query = " ".join(message.command[1:]) if len(message.command) > 1 else None
        if not query and message.reply_to_message and message.reply_to_message.text:
            query = message.reply_to_message.text
        if not query:
            return await message.reply_text(
                "Give a song name or link, e.g. /play faded alan walker"
            )

        if force and not await _require_vc_admin(client, message):
            return

        chat_id = message.chat.id
        status = await message.reply_text(f"🔎 Searching for **{query}**...")

        try:
            info = await music.get_info(query)
        except Exception:
            log.warning("YouTube search failed for %r", query, exc_info=True)
            return await status.edit_text(
                "Couldn't reach YouTube for that search, please try again in a bit."
            )
        if not info:
            return await status.edit_text(f"No results found for **{query}**.")

        if config.DURATION_LIMIT and info["duration_seconds"] > config.DURATION_LIMIT:
            limit_min = config.DURATION_LIMIT // 60
            return await status.edit_text(
                f"That track is longer than the {limit_min} minute limit set for this bot."
            )

        join_error = await _ensure_assistant_in_chat(client, message)
        if join_error:
            return await status.edit_text(join_error)

        file = await music.download(info["id"], video=video)
        if not file:
            return await status.edit_text(
                "Could not download that track, please try another one."
            )

        requester = message.from_user.mention if message.from_user else "someone"
        track = {**info, "file": file, "requested_by": requester}

        already_playing = chat_id in CURRENT
        try:
            if force and already_playing:
                await _change_to(chat_id, track, video)
                await _send_now_playing(
                    status, track,
                    _now_playing_caption("🎶 Now playing:", track, requester, chat_id),
                    buttons=_player_buttons(),
                )
            elif already_playing:
                QUEUES.setdefault(chat_id, []).append(track)
                position = len(QUEUES[chat_id])
                await _send_now_playing(
                    status, track,
                    _now_playing_caption(f"➕ Queued (#{position}):", track, requester),
                )
            else:
                await _join_and_play(chat_id, track, video)
                QUEUES.setdefault(chat_id, [])
                await _send_now_playing(
                    status, track,
                    _now_playing_caption("🎶 Now playing:", track, requester, chat_id),
                    buttons=_player_buttons(),
                )
        except Exception as e:
            log.warning("Failed to start/queue playback in %s", chat_id, exc_info=True)
            await status.edit_text(
                f"❌ Couldn't join/play in this chat's voice chat: {e}\n\n"
                "Make sure a voice chat is actually started in this group, and "
                "that the assistant account isn't already busy elsewhere."
            )

    @app.on_message(filters.command(["play"]) & filters.group)
    async def play_cmd(client, message: Message):
        await _play(client, message, video=False, force=False)

    @app.on_message(filters.command(["vplay"]) & filters.group)
    async def vplay_cmd(client, message: Message):
        await _play(client, message, video=True, force=False)

    @app.on_message(filters.command(["playforce"]) & filters.group)
    async def playforce_cmd(client, message: Message):
        await _play(client, message, video=False, force=True)

    @app.on_message(filters.command(["vplayforce"]) & filters.group)
    async def vplayforce_cmd(client, message: Message):
        await _play(client, message, video=True, force=True)

    @app.on_message(filters.command(["skip"]) & filters.group)
    async def skip_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if chat_id not in CURRENT:
            return await message.reply_text("Nothing is playing right now.")
        LOOPS.pop(chat_id, None)
        next_track = await play_next(chat_id)
        if next_track:
            await message.reply_text(f"⏭ Skipped. Now playing: {next_track['title']}")
        else:
            await message.reply_text("⏭ Skipped. Queue is empty, leaving the voice chat.")

    @app.on_message(filters.command(["stop", "end"]) & filters.group)
    async def stop_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        QUEUES.pop(chat_id, None)
        CURRENT.pop(chat_id, None)
        LOOPS.pop(chat_id, None)
        await _leave(chat_id)
        await message.reply_text("⏹ Stopped and cleared the queue.")

    @app.on_message(filters.command(["pause"]) & filters.group)
    async def pause_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if chat_id not in CURRENT:
            return await message.reply_text("Nothing is playing right now.")
        await calls.pause(chat_id)
        await message.reply_text("⏸ Paused.")

    @app.on_message(filters.command(["resume"]) & filters.group)
    async def resume_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if chat_id not in CURRENT:
            return await message.reply_text("Nothing is playing right now.")
        await calls.resume(chat_id)
        await message.reply_text("▶️ Resumed.")

    @app.on_message(filters.command(["seek"]) & filters.group)
    async def seek_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if chat_id not in CURRENT:
            return await message.reply_text("Nothing is playing right now.")
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text("Please give the number of seconds to seek, e.g. /seek 20")
        new_pos = _elapsed(chat_id) + int(message.command[1])
        await _seek_to(chat_id, new_pos)
        await message.reply_text(f"⏩ Seeked to {new_pos}s.")

    @app.on_message(filters.command(["seekback"]) & filters.group)
    async def seekback_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if chat_id not in CURRENT:
            return await message.reply_text("Nothing is playing right now.")
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text("Please give the number of seconds to seek, e.g. /seekback 20")
        new_pos = max(0, _elapsed(chat_id) - int(message.command[1]))
        await _seek_to(chat_id, new_pos)
        await message.reply_text(f"⏪ Seeked back to {new_pos}s.")

    @app.on_message(filters.command(["restart"]) & filters.group)
    async def restart_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if chat_id not in CURRENT:
            return await message.reply_text("Nothing is playing right now.")
        await _seek_to(chat_id, 0)
        await message.reply_text("🔁 Restarted the current track from 0:00.")

    @app.on_message(filters.command(["loop"]) & filters.group)
    async def loop_cmd(client, message: Message):
        if not await _require_vc_admin(client, message):
            return
        chat_id = message.chat.id
        if len(message.command) < 2 or not message.command[1].isdigit():
            return await message.reply_text("Please give a number between 0 and 10, e.g. /loop 3")
        count = int(message.command[1])
        if not 0 <= count <= 10:
            return await message.reply_text("Please give a number between 0 and 10, e.g. /loop 3")
        if count == 0:
            LOOPS.pop(chat_id, None)
            await message.reply_text("🔁 Looping disabled.")
        else:
            LOOPS[chat_id] = count
            await message.reply_text(f"🔁 Looping the current track {count} time(s).")

    @app.on_message(filters.command(["queue", "q"]) & filters.group)
    async def queue_cmd(client, message: Message):
        chat_id = message.chat.id
        current = CURRENT.get(chat_id)
        if not current:
            return await message.reply_text("Nothing is playing right now.")
        lines = [
            f"🎶 **Now playing:** {current['title']} "
            f"({_fmt_duration(_elapsed(chat_id))}/{current.get('duration', '?')})\n"
            f"Requested by: {current.get('requested_by', 'someone')}"
        ]
        queue = QUEUES.get(chat_id, [])
        if queue:
            lines.append("\n**Up next:**")
            for i, track in enumerate(queue[:10], start=1):
                lines.append(f"{i}. {track['title']} - {track.get('requested_by', 'someone')}")
            if len(queue) > 10:
                lines.append(f"...and {len(queue) - 10} more.")
        await message.reply_text("\n".join(lines))

    # ---------------------------------------------------------- buttons

    @app.on_callback_query(filters.regex("^music_"))
    async def player_buttons_cb(client, query: CallbackQuery):
        chat_id = query.message.chat.id
        action = query.data.split("_", 1)[1]

        if not await is_admin(client, chat_id, query.from_user.id):
            return await query.answer("Only group admins can control playback.", show_alert=True)

        if action != "stop" and chat_id not in CURRENT:
            return await query.answer("Nothing is playing right now.", show_alert=True)

        if action == "pause":
            await calls.pause(chat_id)
            await query.answer("Paused")
        elif action == "resume":
            await calls.resume(chat_id)
            await query.answer("Resumed")
        elif action == "skip":
            LOOPS.pop(chat_id, None)
            next_track = await play_next(chat_id)
            await query.answer("Skipped" if next_track else "Queue empty, left the chat")
        elif action == "stop":
            QUEUES.pop(chat_id, None)
            CURRENT.pop(chat_id, None)
            LOOPS.pop(chat_id, None)
            await _leave(chat_id)
            await query.answer("Stopped")

    # ---------------------------------------------------------- auto-advance

    @calls.on_update()
    async def on_stream_end(_client, update):
        if not isinstance(update, StreamEnded):
            return
        chat_id = update.chat_id

        if LOOPS.get(chat_id, 0) > 0 and chat_id in CURRENT:
            LOOPS[chat_id] -= 1
            await _seek_to(chat_id, 0)
            return

        await play_next(chat_id)

    log.info("🎵 Music feature enabled (voice-chat playback via assistant account).")
