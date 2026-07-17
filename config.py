"""
Central configuration for the sports odds/tips Telegram bot.
Loads everything from environment variables (.env locally, or Railway variables in prod).
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

_broadcast_ids_raw = os.getenv("BROADCAST_CHAT_IDS", "")
BROADCAST_CHAT_IDS = [
    cid.strip() for cid in _broadcast_ids_raw.split(",") if cid.strip()
]

BROADCAST_INTERVAL_HOURS = float(os.getenv("BROADCAST_INTERVAL_HOURS", "6"))

# Your own Telegram chat ID — required to use /addtip. Get it from /whoami
# after the bot is running, then add it as ADMIN_CHAT_ID in Railway variables.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# How often (minutes) to check for newly-live matches
LIVE_CHECK_INTERVAL_MINUTES = float(os.getenv("LIVE_CHECK_INTERVAL_MINUTES", "5"))

SUPPORTED_SPORTS = {
    "football": "soccer_epl",
    "basketball": "basketball_nba",
    "tennis": "tennis_atp_wimbledon",
    "americanfootball": "americanfootball_nfl",
    "baseball": "baseball_mlb",
}

DISCLAIMER = (
    "⚠️ *Informational only.* Odds, scores, and tips shared here are for information "
    "and entertainment purposes only. Nothing here is a guaranteed outcome or financial "
    "advice. Betting carries risk — only wager what you can afford to lose, and please "
    "gamble responsibly. Must be of legal gambling age in your jurisdiction. If gambling "
    "is affecting you negatively, please seek help from a local support service."
)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Add it to your .env or Railway variables.")
