"""
Sports odds/scores/tips Telegram bot — informational only.

Commands:
  /start          - welcome + disclaimer
  /sports         - list supported sports
  /odds <sport>   - current odds (e.g. /odds football)
  /scores <sport> - recent/live scores (e.g. /scores basketball)
  /bet9ja <league>- Bet9ja-specific soccer odds (e.g. /bet9ja epl)
  /tips           - latest manual picks/analysis (edit TIPS list below)
"""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    TELEGRAM_BOT_TOKEN,
    SUPPORTED_SPORTS,
    DISCLAIMER,
    BROADCAST_CHAT_IDS,
    BROADCAST_INTERVAL_HOURS,
)
from odds_service import get_odds, get_scores, format_odds, format_scores, OddsServiceError
from bet9ja_service import get_bet9ja_odds, format_bet9ja_odds, Bet9jaServiceError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Manual tips/picks -------------------------------------------------
# Edit this list to post your own analysis. Each entry is one tip.
# Keep the framing as opinion/analysis, never "guaranteed" language.
TIPS = [
    "Add your own picks here — e.g. 'Arsenal vs Chelsea: Arsenal have won 4 of "
    "the last 5 meetings at home, odds currently favor a narrow win.'",
]


# --- Command handlers ---------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome! I send sports odds, scores, and tips.\n\n"
        "Commands:\n"
        "/sports — list supported sports\n"
        "/odds <sport> — current odds\n"
        "/scores <sport> — recent/live scores\n"
        "/bet9ja <league> — Bet9ja soccer odds\n"
        "/tips — latest picks\n\n"
        f"{DISCLAIMER}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def sports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    listing = "\n".join(f"• {name}" for name in SUPPORTED_SPORTS)
    await update.message.reply_text(f"Supported sports:\n{listing}")


async def odds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /odds <sport>  e.g. /odds football")
        return
    sport = context.args[0]
    try:
        events = get_odds(sport)
        message = format_odds(events)
    except OddsServiceError as e:
        message = f"⚠️ {e}"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def scores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scores <sport>  e.g. /scores basketball")
        return
    sport = context.args[0]
    try:
        events = get_scores(sport)
        message = format_scores(events)
    except OddsServiceError as e:
        message = f"⚠️ {e}"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def bet9ja(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league = context.args[0] if context.args else "epl"
    try:
        matches = get_bet9ja_odds(league)
        message = format_bet9ja_odds(matches)
    except Bet9jaServiceError as e:
        message = f"⚠️ {e}"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    body = "\n\n".join(f"📌 {t}" for t in TIPS)
    text = f"{body}\n\n_These are analysis/opinion, not guarantees._"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# --- Scheduled broadcast --------------------------------------------------

async def broadcast_job(application: Application):
    if not BROADCAST_CHAT_IDS:
        return
    for sport in SUPPORTED_SPORTS:
        try:
            events = get_odds(sport)
            message = f"*{sport.title()} odds update:*\n\n" + format_odds(events, limit=3)
        except OddsServiceError as e:
            message = f"⚠️ Could not fetch {sport} odds: {e}"

        for chat_id in BROADCAST_CHAT_IDS:
            try:
                await application.bot.send_message(
                    chat_id=chat_id, text=message, parse_mode=ParseMode.MARKDOWN
                )
            except Exception as exc:
                logger.warning("Failed to broadcast to %s: %s", chat_id, exc)


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sports", sports))
    application.add_handler(CommandHandler("odds", odds))
    application.add_handler(CommandHandler("scores", scores))
    application.add_handler(CommandHandler("bet9ja", bet9ja))
    application.add_handler(CommandHandler("tips", tips))

    if BROADCAST_CHAT_IDS:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            broadcast_job,
            "interval",
            hours=BROADCAST_INTERVAL_HOURS,
            args=[application],
        )
        scheduler.start()
        logger.info(
            "Scheduled broadcasts every %s hours to %s chats",
            BROADCAST_INTERVAL_HOURS,
            len(BROADCAST_CHAT_IDS),
        )

    logger.info("Bot starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
