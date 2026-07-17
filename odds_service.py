"""
Wrapper around The Odds API (https://the-odds-api.com) for odds + scores.
Covers major global bookmakers across football, basketball, tennis, etc.
Does NOT cover Bet9ja/SportyBet specifically — see bet9ja_service.py for that.
"""
import requests
from config import ODDS_API_KEY, SUPPORTED_SPORTS

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsServiceError(Exception):
    pass


def _check_key():
    if not ODDS_API_KEY:
        raise OddsServiceError(
            "No ODDS_API_KEY configured. Get a free key at https://the-odds-api.com "
            "and add it to your environment variables."
        )


def get_odds(sport: str, regions: str = "uk,eu,us", markets: str = "h2h"):
    """
    Fetch current odds for a sport.
    sport: friendly key from SUPPORTED_SPORTS (e.g. 'football', 'basketball')
    Returns a list of event dicts, or raises OddsServiceError.
    """
    _check_key()
    sport_key = SUPPORTED_SPORTS.get(sport.lower())
    if not sport_key:
        raise OddsServiceError(
            f"Unknown sport '{sport}'. Supported: {', '.join(SUPPORTED_SPORTS)}"
        )

    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        raise OddsServiceError(f"Odds API error ({resp.status_code}): {resp.text[:200]}")
    return resp.json()


def get_scores(sport: str, days_from: int = 1):
    """
    Fetch recent/live scores for a sport.
    days_from: how many days back to include completed games (max 3).
    """
    _check_key()
    sport_key = SUPPORTED_SPORTS.get(sport.lower())
    if not sport_key:
        raise OddsServiceError(
            f"Unknown sport '{sport}'. Supported: {', '.join(SUPPORTED_SPORTS)}"
        )

    url = f"{BASE_URL}/sports/{sport_key}/scores"
    params = {"apiKey": ODDS_API_KEY, "daysFrom": days_from}
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        raise OddsServiceError(f"Odds API error ({resp.status_code}): {resp.text[:200]}")
    return resp.json()


def format_odds(events: list, limit: int = 5) -> str:
    """Turn raw odds JSON into a readable Telegram message."""
    if not events:
        return "No upcoming events found for this sport right now."

    lines = []
    for event in events[:limit]:
        home = event.get("home_team", "Home")
        away = event.get("away_team", "Away")
        commence = event.get("commence_time", "TBD")
        lines.append(f"*{home}* vs *{away}*  _(kickoff: {commence})_")

        bookmakers = event.get("bookmakers", [])[:3]
        if not bookmakers:
            lines.append("  No odds posted yet.")
        for bm in bookmakers:
            title = bm.get("title", "Bookmaker")
            h2h = next((m for m in bm.get("markets", []) if m["key"] == "h2h"), None)
            if h2h:
                outcomes = ", ".join(
                    f"{o['name']} @ {o['price']}" for o in h2h.get("outcomes", [])
                )
                lines.append(f"  • {title}: {outcomes}")
        lines.append("")  # spacer
    return "\n".join(lines)


def format_scores(events: list, limit: int = 5) -> str:
    """Turn raw scores JSON into a readable Telegram message."""
    if not events:
        return "No recent scores found for this sport right now."

    lines = []
    for event in events[:limit]:
        home = event.get("home_team", "Home")
        away = event.get("away_team", "Away")
        completed = event.get("completed", False)
        scores = event.get("scores")

        if scores:
            score_str = " - ".join(s["score"] for s in scores)
            status = "Final" if completed else "Live"
            lines.append(f"*{home}* {score_str} *{away}*  _({status})_")
        else:
            lines.append(f"*{home}* vs *{away}*  _(not started / no score yet)_")
    return "\n".join(lines)
