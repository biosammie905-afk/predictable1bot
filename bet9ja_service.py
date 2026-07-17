"""
Wrapper around the community NaijaBet_Api library for Bet9ja soccer odds.
NOTE: this is an unofficial, community-maintained library that reads Bet9ja's
public site data. It covers 1X2 soccer odds only, and may break if Bet9ja
changes their site structure — wrapped in try/except so the bot won't crash.
"""

try:
    from NaijaBet_Api.bookmakers import bet9ja as bet9ja_module
    from NaijaBet_Api.id import Betid
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


class Bet9jaServiceError(Exception):
    pass


LEAGUE_MAP = {
    "epl": "PREMIERLEAGUE",
    "premierleague": "PREMIERLEAGUE",
    # Add more league names here as needed — check NaijaBet_Api's Betid
    # enum (NaijaBet_Api/id.py on GitHub) for what's supported.
}


def get_bet9ja_odds(league: str = "epl"):
    """
    Fetch Bet9ja 1X2 odds for a given league (soccer only).
    Returns a list of dicts like:
      {'home': 4.0, 'draw': 3.75, 'away': 1.92, 'match': 'Team A - Team B',
       'league': 'Premier League', 'match_id': 123, 'time': 1628881200000}
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
        b9 = bet9ja_module.Bet9ja()
        betid = getattr(Betid, league_key)
        return b9.get_league(betid)
    except Exception as exc:
        raise Bet9jaServiceError(f"Could not fetch Bet9ja odds right now: {exc}")


def format_bet9ja_odds(matches: list, limit: int = 5) -> str:
    if not matches:
        return "No Bet9ja odds available for this league right now."

    lines = ["Bet9ja odds:"]
    for m in matches[:limit]:
        match_name = m.get("match", "Unknown match")
        home = m.get("home")
        draw = m.get("draw")
        away = m.get("away")
        lines.append(f"• {match_name} — Home: {home}, Draw: {draw}, Away: {away}")
    return "\n".join(lines)
