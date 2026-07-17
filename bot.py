"""
Sports odds/scores/tips Telegram bot — informational only.

Commands:
  /start            - welcome + disclaimer
  /whoami           - show your chat ID (needed for ADMIN_CHAT_ID / notifications)
  /sports           - list supported sports
  /odds <sport>     - current odds (e.g. /odds football)
  /scores <sport>   - recent/live scores (e.g. /scores basketball)
  /bet9ja <league>  - Bet9ja-specific soccer odds (e.g. /bet9ja epl)
  /tips             - latest picks/analysis
  /addtip <text>    - admin only: add a new tip
  /notifyon         - subscribe this chat to live match alerts
  /notifyoff        - unsubscribe this chat from live match alerts
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
    ADMIN_CHAT_ID,
    LIVE_CHECK_INTERVAL_MINUTES,
)
from odds_service import get_odds, get_scores, format_odds, format_scores, OddsServiceError
from bet9ja_service import get_bet9ja_odds, format_bet9ja_odds, Bet9jaServiceError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- In-memory state (resets on restart/redeploy) ---
TIPS = [
    "Add your own picks with /addtip <text>, or edit this list directly in bot.py.",
]
NOTIFY_SUBSCRIBERS = set()   # chat_ids subscribed to live match alerts
_SEEN_LIVE_MATCHES = set()   # match keys already notified, to avoid repeat pings


# --- Basic commands ---------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome! I send sports odds, scores, and tips.\n\n"
        "Commands:\n"
        "/sports — list supported sports\n"
        "/odds <sport> — current odds\n"
        "/scores <sport> — recent/live scores\n"
        "/bet9ja <league> — Bet9ja soccer odds\n"
        "/tips — latest picks\n"
        "/notifyon — get pinged when a match goes live\n"
        "/notifyoff — stop live match alerts\n"
        "/whoami — show your chat ID\n\n"
        f"{DISCLAIMER}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Your chat ID is: {chat_id}\n\n"
        "Set this as ADMIN_CHAT_ID in Railway if you want /addtip access."
    )


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
    # No parse_mode here — scraped match/league names can contain characters
    # that break Telegram's Markdown parser and silently fail to send.
    await update.message.reply_text(message)


async def tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    body = "\n\n".join(f"📌 {t}" for t in TIPS)
    text = f"{body}\n\nThese are analysis/opinion, not guarantees."
    await update.message.reply_text(text)


async def addtip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not ADMIN_CHAT_ID or chat_id != str(ADMIN_CHAT_ID):
        await update.message.reply_text(
            "⛔ Only the bot admin can add tips. Run /whoami and set ADMIN_CHAT_ID in Railway."
        )
        return
    if not context.args:
        await update.message.reply_text("Usage: /addtip <your pick/analysis text>")
        return
    new_tip = " ".join(context.args)
    TIPS.append(new_tip)
    await update.message.reply_text(f"✅ Tip added:\n{new_tip}")


async def notifyon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    NOTIFY_SUBSCRIBERS.add(chat_id)
    await update.message.reply_text("🔔 You'll now be pinged here when a match goes live.")


async def notifyoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    NOTIFY_SUBSCRIBERS.discard(chat_id)
    await update.message.reply_text("🔕 Live match alerts turned off for this chat.")


# --- Scheduled jobs -------------------------------------------------------

async def broadcast_job(application: Application):
    """Periodic odds summary to BROADCAST_CHAT_IDS (optional feature)."""
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


async def live_match_check_job(application: Application):
    """Checks each sport for newly-live matches and pings subscribers once each."""
    if not NOTIFY_SUBSCRIBERS:
        return

    for sport in SUPPORTED_SPORTS:
        try:
            events = get_scores(sport)
        except OddsServiceError as e:
            logger.warning("Live check failed for %s: %s", sport, e)
            continue

        for event in events:
            if event.get("completed"):
                continue
            scores_data = event.get("scores")
            if not scores_data:
                continue  # not started yet, no live score to report

            match_key = event.get("id") or f"{event.get('home_team')}-{event.get('away_team')}"
            if match_key in _SEEN_LIVE_MATCHES:
                continue

            _SEEN_LIVE_MATCHES.add(match_key)
            home = event.get("home_team", "Home")
            away = event.get("away_team", "Away")
            score_str = " - ".join(s["score"] for s in scores_data)
            message = f"🔴 Live now: {home} {score_str} {away} ({sport})"

            for chat_id in NOTIFY_SUBSCRIBERS:
                try:
                    await application.bot.send_message(chat_id=chat_id, text=message)
                except Exception as exc:
                    logger.warning("Failed to notify %s: %s", chat_id, exc)


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(CommandHandler("sports", sports))
    application.add_handler(CommandHandler("odds", odds))
    application.add_handler(CommandHandler("scores", scores))
    application.add_handler(CommandHandler("bet9ja", bet9ja))
    application.add_handler(CommandHandler("tips", tips))
    application.add_handler(CommandHandler("addtip", addtip))
    application.add_handler(CommandHandler("notifyon", notifyon))
    application.add_handler(CommandHandler("notifyoff", notifyoff))

    scheduler = AsyncIOScheduler()

    if BROADCAST_CHAT_IDS:
        scheduler.add_job(
            broadcast_job, "interval", hours=BROADCAST_INTERVAL_HOURS, args=[application]
        )

    scheduler.add_job(
        live_match_check_job,
        "interval",
        minutes=LIVE_CHECK_INTERVAL_MINUTES,
        args=[application],
    )
    scheduler.start()

    logger.info("Bot starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
