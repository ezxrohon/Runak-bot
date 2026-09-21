# ============================================================
# 🫧🦋 ʀuɴAk - Telegram Group Manager + Economy Bot
# Owner: @rohon_x04
# Deploy target: Render (Background Worker / Web Service)
# ============================================================

import os
os.environ["PATH"] = os.getcwd() + os.pathsep + os.environ.get("PATH", "")
import asyncio

# One single event loop for the whole process. Pyrogram/PyTgCalls objects
# constructed below (app, and handlers.music's userbot/calls at import
# time) can grab a reference to "the current loop" during construction -
# if we later ran everything via asyncio.run() instead, that call creates
# a brand new, DIFFERENT loop, and anything holding a reference to this
# first one ends up attached to the wrong loop. That mismatch is exactly
# what caused the "got Future ... attached to a different loop" crash.
# Using loop.run_until_complete() below instead of asyncio.run() keeps it
# to one loop for the entire run.
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import logging
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

print("🚀 Starting ʀuɴAk...")

try:
    print("🔍 Checking ENV variables...")
    for key in ("API_ID", "API_HASH", "BOT_TOKEN", "FIREBASE_URL", "OWNER_ID"):
        val = os.getenv(key)
        print(f"{key}:", "SET" if val else "❌ MISSING")
    # Optional but worth surfacing at boot - a silently-unset LOG_CHAT_ID
    # is the #1 reason "the bot doesn't send anything to my log channel".
    print("LOG_CHAT_ID:", os.getenv("LOG_CHAT_ID") or "not set (log channel disabled)")
except Exception as e:
    print("❌ ENV ERROR:", e)
    traceback.print_exc()

# ------------------------------------------------------------
# Render needs an open HTTP port for "Web Service" type deploys
# so it doesn't think the app crashed. This is a plain health
# check endpoint - it does nothing else.
# ------------------------------------------------------------
PORT = int(os.environ.get("PORT", 10000))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ruNAk is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # keep the logs quiet


def start_web_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        logging.info(f"🌐 Health server running on port {PORT}")
        server.serve_forever()
    except Exception as e:
        print("❌ WEB SERVER ERROR:", e)
        traceback.print_exc()


threading.Thread(target=start_web_server, daemon=True).start()

try:
    from pyrogram import Client, idle
    from config import API_ID, API_HASH, BOT_TOKEN
    from handlers import register_all_handlers
    from handlers.music import MUSIC_ENABLED, userbot, calls

    print("🔧 Initializing bot client...")

    app = Client(
        "runak_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    register_all_handlers(app)

    async def _main():
        print("🚀 ʀuɴAk is starting...")
        await app.start()
        if MUSIC_ENABLED:
            print("🎵 Starting music assistant + voice-chat client...")
            await userbot.start()
            await calls.start()
        print("✅ ʀuɴAk is up.")
        await idle()
        print("🛑 Shutting down...")
        if MUSIC_ENABLED:
            await userbot.stop()
        await app.stop()

    loop.run_until_complete(_main())
    print("🛑 Bot stopped")

except Exception as e:
    print("💥 BOT CRASHED:", e)
    traceback.print_exc()
