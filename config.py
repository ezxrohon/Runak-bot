# ============================================================
# 🫧🦋 ʀuɴAk - Telegram Group Manager + Economy Bot
# Owner: @rohon_x04
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# ---- Telegram API (from https://my.telegram.org) ----
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ---- Database: Firebase Realtime Database ----
# FIREBASE_URL looks like: https://your-project-default-rtdb.firebaseio.com
# FIREBASE_SECRET is the legacy database secret (Project settings -> Service
# accounts -> Database secrets). Leave it blank ONLY if your database rules
# are set to public test-mode (".read": true, ".write": true) - fine for
# quick testing, NOT fine for anything real.
FIREBASE_URL = os.getenv("FIREBASE_URL", "").rstrip("/")
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET", "")

# ---- Owner / Bot info ----
OWNER_ID = int(os.getenv("OWNER_ID", 0))          # numeric Telegram user ID of @rohon_x04
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "rohon_x04")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")       # e.g. RunAkBot (without @)
BOT_NAME = os.getenv("BOT_NAME", "🫧🦋ʀuɴAk")

# ---- Links & visuals ----
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/+")
UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "https://t.me/+")
START_IMAGE = os.getenv("START_IMAGE", "")

# ---- Economy tuning ----
CURRENCY_NAME = os.getenv("CURRENCY_NAME", "Bubbles")
CURRENCY_EMOJI = os.getenv("CURRENCY_EMOJI", "🫧")
DAILY_REWARD = int(os.getenv("DAILY_REWARD", 1000))
STARTING_BALANCE = int(os.getenv("STARTING_BALANCE", 100))
ROB_COOLDOWN_MIN = int(os.getenv("ROB_COOLDOWN_MIN", 30))

# ---- PvP: kill / protection tuning ----
KILL_COOLDOWN_MIN = int(os.getenv("KILL_COOLDOWN_MIN", 60))
KILL_SUCCESS_RATE = float(os.getenv("KILL_SUCCESS_RATE", 0.4))
PROTECTION_HOURS = int(os.getenv("PROTECTION_HOURS", 24))  # protected while dead / just after being killed
REVIVE_COST = int(os.getenv("REVIVE_COST", 1000))

# ---- Optional AI chat (leave blank to disable) ----
AI_API_KEY = os.getenv("AI_API_KEY", "")           # e.g. a Mistral/Groq API key
AI_ENABLED = bool(AI_API_KEY)
