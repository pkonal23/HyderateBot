# 💧 Funky Hydration Bot

A Telegram bot that reminds you to drink water every 2 hours — funky messages, streak tracking, no AI or external APIs beyond Telegram.

## Features
- Randomized, personality-packed reminder messages (uses your Telegram first name)
- Time-of-day greetings (Good morning / afternoon / evening) based on Indian Standard Time
- Quiet hours — no reminders fire 11 PM–7 AM IST by default, regardless of where it's hosted
- ✅ inline button to log a drink, with streak + total counters
- `/status`, `/start`, `/stop` commands
- Data stored in a plain local JSON file — no database required

## Setup

1. **Create a bot with [@BotFather](https://t.me/BotFather)** on Telegram — send `/newbot` and follow the prompts. Copy the token it gives you.
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set your bot token as an environment variable:**
   ```bash
   export TELEGRAM_BOT_TOKEN='your-token-here'
   ```
4. **Run it:**
   ```bash
   python hydration_bot.py
   ```
5. Message your bot `/start` on Telegram.

## Configuration

Open `hydration_bot.py` and adjust:
- `REMINDER_INTERVAL_SECONDS` — how often reminders fire (default: 2 hours)
- `QUIET_HOURS_START` / `QUIET_HOURS_END` — the no-reminders window, in 24-hour IST (default: 23 → 7, i.e. 11 PM–7 AM)
- `FUNKY_MESSAGES` / `CHEER_MESSAGES` / `GREETINGS` — add your own lines
- `DATA_FILE` — defaults to `hydration_data.json`; can be overridden via the `DATA_FILE` env var (useful for pointing at a mounted volume on hosts with ephemeral storage)

## Deploying

The bot needs to run continuously to fire reminders (it uses polling, not a public webhook). Options:
- Leave it running on your own computer / a Raspberry Pi
- Deploy as a background service on a host like [Railway](https://railway.com) — see deployment notes below
- Run on a permanently-free VM like an Oracle Cloud Always Free instance

### Deploying on Railway
1. Push this repo to GitHub, then in Railway: **New Project → Deploy from GitHub repo**.
2. In the service's **Variables** tab, add `TELEGRAM_BOT_TOKEN`.
3. In **Settings → Deploy**, set the **Custom Start Command** to `python hydration_bot.py`.
4. Check the **Logs** tab for `💧 Hydration bot is running...`, then test `/start` on Telegram.
5. Optional: add a Railway **Volume** mounted at `/data`, and set `DATA_FILE=/data/hydration_data.json` so your streak survives redeploys.

Note: Railway's free tier includes a 30-day/$5 trial, then drops to $1/month of usage credit — keep an eye on usage in the dashboard.
