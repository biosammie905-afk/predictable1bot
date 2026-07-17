"""
Wrapper around the community NaijaBet_Api library for Bet9ja soccer odds.
NOTE: this is an unofficial, community-maintained library that reads Bet9ja's
public site data. It covers 1X2 / doublechance soccer odds only, and may break
if Bet9ja changes their site structure — wrap calls in try/except in the bot.
"""

try:
    from NaijaBet_Api.bookmakers import Bet9ja
    from NaijaBet_Api.id import Betid
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class Bet9jaServiceError(Exception):
    pass


LEAGUE_MAP = {
    "epl": "PREMIERLEAGUE",
    "premierleague": "PREMIERLEAGUE",
    # Extend this map with more Betid entries as needed —
    # check the NaijaBet_Api package for the full list of supported leagues.
}


def get_bet9ja_odds(league: str = "epl"):
    """
    Fetch Bet9ja 1X2 odds for a given league (soccer only).
    Returns a list of match odds dicts, or raises Bet9jaServiceError.
    """
    if not _AVAILABLE:
        raise Bet9jaServiceError(
            "NaijaBet_Api is not installed. Run: pip install NaijaBet-Api"
        )

    league_key = LEAGUE_MAP.get(league.lower())
    if not league_key:
        raise Bet9jaServiceError(
            f"Unknown league '{league}'. Supported: {', '.join(LEAGUE_MAP)}"
        )

    try:
        bet9ja = Bet9ja()
        betid = getattr(Betid, league_key)
        return bet9ja.get_league(betid)
    except Exception as exc:
        # Community library hitting a live site — treat any failure as
        # a soft "unavailable right now" rather than crashing the bot.
        raise Bet9jaServiceError(f"Could not fetch Bet9ja odds right now: {exc}")


def format_bet9ja_odds(matches: list, limit: int = 5) -> str:
    if not matches:
        return "No Bet9ja odds available for this league right now."

    lines = ["*Bet9ja odds:*"]
    for m in matches[:limit]:
        # Field names depend on NaijaBet_Api's return format — adjust if the
        # library's schema differs from this example.
        home = m.get("home_team", "Home")
        away = m.get("away_team", "Away")
        odds = m.get("odds", {})
        odds_str = ", ".join(f"{k}: {v}" for k, v in odds.items()) if odds else "N/A"
        lines.append(f"• *{home}* vs *{away}* — {odds_str}")
    return "\n".join(lines)
