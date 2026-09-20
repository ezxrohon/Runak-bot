# 🫧🦋 ʀuɴAk

A Telegram group management bot with a fun/economy side, built with **Pyrogram** + **MongoDB**.

**Owner:** [@rohon_x04](https://t.me/rohon_x04)

## Features

- **Moderation:** kick, ban, unban, mute, unmute, warn, warns, resetwarns, promote, demote
- **Locks:** block URLs, stickers, media, @usernames, or forwards per-group
- **Welcome:** custom welcome messages with placeholders, on/off toggle
- **Group log:** posts to a private log group whenever the bot is added to or removed from a group
- **Games:** a multiplayer card game (`/card /bet /flip`), casino machines (`/jackpot /mines /roulette`), and PvP duels (`/ttt /rps`) — see the in-bot 🎮 Games help menu
- **Economy (Bubbles 🫧):** balance, daily reward, give, rob, leaderboard
- **Shop:** buy cosmetic items with Bubbles, /inventory
- **Fun & Games:** /roll /flip /8ball /rps /guess /hug /slap /pat /quote
- **Owner tools:** /broadcast, /stats

## 1. Get your credentials

| Credential | Where to get it |
|---|---|
| `API_ID` / `API_HASH` | https://my.telegram.org → API Development Tools |
| `BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather), `/newbot` |
| `FIREBASE_URL` | https://console.firebase.google.com → new project → Build → Realtime Database → Create Database. Copy the URL shown (ends in `firebaseio.com`) |
| `FIREBASE_SECRET` | Project settings (gear icon) → Service accounts → Database secrets. If your project doesn't show that tab, leave blank and use open test-mode rules instead (see below) |
| `OWNER_ID` | Message [@userinfobot](https://t.me/userinfobot), it replies with your numeric ID |
| `LOG_CHAT_ID` | *(optional)* Numeric chat ID of a private log group you create and add the bot to — it posts there whenever it's added to or removed from a group. Get the ID by forwarding a message from that group to [@userinfobot](https://t.me/userinfobot), or leave blank to disable |

**About `FIREBASE_SECRET`:** Google is phasing out legacy database secrets, so newer Firebase projects may not offer one. If yours doesn't, leave `FIREBASE_SECRET` blank and instead open your Realtime Database → **Rules** tab and set:

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

This makes the database publicly readable/writable by anyone who knows the URL — fine while you're testing, but **not** something to leave in place for a bot people will actually add to their groups. Once you're ready to go live, either dig up a database secret (older projects still have the option) or ask me to switch the auth over to a Firebase service-account token instead.

Copy `.env.example` to `.env` and fill in the values for local testing.

## 2. Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## 3. Deploy on Render

1. Push this project to a GitHub repo.
2. On [Render](https://render.com), create a **New → Background Worker** (not Web Service — this bot doesn't need to serve HTTP traffic, though `main.py` also opens a health-check port in case you pick Web Service instead).
3. Connect your repo.
4. Build command: `pip install -r requirements.txt`
5. Start command: `python3 main.py` (already set via the `Procfile`)
6. Add every variable from `.env.example` under **Environment → Environment Variables**.
7. Deploy. Check the logs — you should see `✅ Firebase Realtime Database configured` and `🚀 ʀuɴAk is starting...`.

## Notes

- Never commit `.env` or paste real tokens into files you share — `.gitignore` already excludes it.
- If a bot token or database credential is ever exposed publicly, regenerate it immediately via @BotFather / your Firebase project settings.
- Firebase's free Spark plan caps simultaneous connections and daily bandwidth — fine for a bot in a handful of groups, worth checking [Firebase's pricing page](https://firebase.google.com/pricing) if this grows large.
- Structured with inspiration from LearningBotsOfficial's Nomade group-manager skeleton and RoxxOP's Baka economy/fun plugins — rebuilt and rebranded for ʀuɴAk.
