"""
💧 FUNKY HYDRATION BOT 💧
A Telegram bot that nags you (lovingly) to drink water every N hours.
No AI, no APIs beyond Telegram — just a scheduler and personality.
"""

import os
import json
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─────────────────────────────
# ⚙️ CONFIG — tweak these
# ─────────────────────────────
REMINDER_INTERVAL_SECONDS = 2 * 60 * 60   # every 2 hours. Change to e.g. 60*30 for testing (30 min).
FIRST_REMINDER_DELAY = 15                 # seconds after /start before the first ping (kept short for testing)
# Point this at a mounted volume path (e.g. "/data/hydration_data.json") on hosts
# with ephemeral filesystems, so your streak survives redeploys/restarts.
DATA_FILE = os.environ.get("DATA_FILE", "hydration_data.json")

# All time-of-day logic runs in Indian Standard Time, regardless of what
# timezone the server/host itself is set to.
TIMEZONE = ZoneInfo("Asia/Kolkata")

# Quiet hours: no reminders fire in this window. Wraps past midnight.
# Default: 11 PM – 7 AM IST. Change these two numbers (24-hour clock) to adjust.
QUIET_HOURS_START = 23  # 11 PM
QUIET_HOURS_END = 7     # 7 AM

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────
# 🎉 FUNKY MESSAGE BANK
# Add as many as you want — one is picked at random each time.
# {name} gets replaced with the person's Telegram first name.
# ─────────────────────────────
FUNKY_MESSAGES = [
    "💧 Yo {name}! Your cells are staging a *dehydration protest*. Water. Now. 🚰",
    "🐫 {name}, you are NOT a camel. Drink some water, superstar. ✨",
    "🌊 Ding ding ding! Hydration o'clock, {name}! Chug-a-lug time. 🥤",
    "🔥 {name}, your skin just texted. It wants H2O, stat. 💦",
    "🚀 Water break, {name}! Fuel the human rocket. 🧑‍🚀💧",
    "🎉 SURPRISE! It's the water fairy again, {name}. Sip sip hooray! 🧚💧",
    "🧠 Fun fact: your brain is ~75% water, {name}. Top it off. 🥛",
    "🪩 {name}, it's hydration o'clock — time to disco with your water bottle. 💃💧",
    "🌵 Don't be a cactus, {name}. Cacti barely drink and look how prickly they are. 🌊",
    "🦄 A magical water reminder has appeared, {name}! Use it wisely. 🧙‍♀️💧",
]

CHEER_MESSAGES = [
    "🙌 Nice one, {name}! Streak: {streak} 🔥 | Total sips logged: {total} 💧",
    "🎊 Splash! {name} hydrates again. Streak: {streak} 🔥 Total: {total} 💧",
    "💪 {name} the Hydration Champion strikes! Streak: {streak} 🔥 Total: {total} 💧",
    "🌟 Look at {name} go! Streak: {streak} 🔥 Total: {total} 💧",
]

# Time-of-day greetings, picked at random alongside the funky message.
# Kept name-free so they can be combined with FUNKY_MESSAGES without repeating the name.
GREETINGS = {
    "morning": ["🌅 Good morning!", "☀️ Rise and shine!", "🐓 Morning, sunshine!"],
    "afternoon": ["🌞 Good afternoon!", "🕑 Afternoon check-in!", "🥤 Midday hydration alert!"],
    "evening": ["🌆 Good evening!", "🌇 Evening vibes!", "🌃 Winding-down water check!"],
}

# ─────────────────────────────
# 🕰️ IST time helpers
# ─────────────────────────────
def now_ist() -> datetime:
    return datetime.now(TIMEZONE)


def is_quiet_hours(now: datetime | None = None) -> bool:
    """True if we're inside the no-reminders window (wraps past midnight)."""
    now = now or now_ist()
    hour = now.hour
    if QUIET_HOURS_START > QUIET_HOURS_END:
        # e.g. 23 -> 7: quiet if hour >= 23 OR hour < 7
        return hour >= QUIET_HOURS_START or hour < QUIET_HOURS_END
    # non-wrapping window, e.g. 1 -> 5
    return QUIET_HOURS_START <= hour < QUIET_HOURS_END


def time_bucket(now: datetime | None = None) -> str:
    """Returns 'morning', 'afternoon', or 'evening' based on IST hour."""
    now = now or now_ist()
    hour = now.hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    else:
        return "evening"


def greeting_word(now: datetime | None = None) -> str:
    """Plain 'Good morning' / 'Good afternoon' / 'Good evening' for use in sentences."""
    bucket = time_bucket(now)
    return {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening"}[bucket]


# ─────────────────────────────
# 💾 Tiny JSON "database" — no server needed
# ─────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─────────────────────────────
# 🤖 Handlers
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = update.effective_user.first_name or "friend"

    data = load_data()
    data.setdefault(str(chat_id), {"name": name, "streak": 0, "total": 0})
    save_data(data)

    # Cancel any existing reminder job for this chat before making a new one
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()

    context.job_queue.run_repeating(
        send_reminder,
        interval=REMINDER_INTERVAL_SECONDS,
        first=FIRST_REMINDER_DELAY,
        chat_id=chat_id,
        name=str(chat_id),
    )

    hours = REMINDER_INTERVAL_SECONDS / 3600
    quiet_start_12h = f"{QUIET_HOURS_START % 12 or 12} {'AM' if QUIET_HOURS_START < 12 else 'PM'}"
    quiet_end_12h = f"{QUIET_HOURS_END % 12 or 12} {'AM' if QUIET_HOURS_END < 12 else 'PM'}"
    await update.message.reply_text(
        f"{greeting_word()}, {name}! 💦 I'm your funky hydration hype-bot.\n\n"
        f"I'll ping you every {hours:g} hours to remind you to drink water "
        f"(IST time, quiet between {quiet_start_12h}–{quiet_end_12h}). "
        f"Tap the button when you do, and we'll build a streak! 🔥\n\n"
        f"Commands:\n"
        f"/status — check your streak\n"
        f"/stop — pause reminders\n"
        f"/start — resume reminders"
    )


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    now = now_ist()

    if is_quiet_hours(now):
        logger.info(f"Skipping reminder for chat {chat_id} — quiet hours (IST {now:%H:%M})")
        return

    data = load_data()
    name = data.get(str(chat_id), {}).get("name", "friend")

    greeting = random.choice(GREETINGS[time_bucket(now)])
    funky = random.choice(FUNKY_MESSAGES).format(name=name)
    msg = f"{greeting}\n{funky}"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ I drank water!", callback_data="drank")]]
    )
    await context.bot.send_message(
        chat_id=chat_id, text=msg, reply_markup=keyboard, parse_mode="Markdown"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="💧 Logged!")

    chat_id = query.message.chat_id
    data = load_data()
    entry = data.setdefault(
        str(chat_id),
        {"name": query.from_user.first_name or "friend", "streak": 0, "total": 0},
    )
    entry["streak"] += 1
    entry["total"] += 1
    save_data(data)

    cheer = random.choice(CHEER_MESSAGES).format(
        name=entry["name"], streak=entry["streak"], total=entry["total"]
    )
    await query.edit_message_text(cheer)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = load_data()
    entry = data.get(str(chat_id))
    if not entry:
        await update.message.reply_text("You haven't started yet! Type /start first. 🚰")
        return
    await update.message.reply_text(
        f"📊 {entry['name']}'s Hydration Stats\n"
        f"Streak: {entry['streak']} 🔥\n"
        f"Total logged: {entry['total']} 💧"
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("Reminders paused. Type /start to resume anytime! 🛑💧")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "❌ Set the TELEGRAM_BOT_TOKEN environment variable first!\n"
            "   export TELEGRAM_BOT_TOKEN='your-token-here'"
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("💧 Hydration bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
