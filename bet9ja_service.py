"""
Wrapper around the community NaijaBet_Api library for Bet9ja soccer odds.
NOTE: this is an unofficial, community-maintained library that reads Bet9ja's
public site data. Its import style has changed between versions/docs, so this
tries multiple known import patterns and uses whichever one actually works.
"""

_AVAILABLE = False
_IMPORT_ERROR = None
Bet9jaClass = None
Betid = None

# Try pattern 1: lowercase module, e.g. `from NaijaBet_Api.bookmakers import bet9ja`
try:
    from NaijaBet_Api.bookmakers import bet9ja as _bet9ja_module
    from NaijaBet_Api.id import Betid as _Betid
    Bet9jaClass = _bet9ja_module.Bet9ja
    Betid = _Betid
    _AVAILABLE = True
except Exception as e1:
    # Try pattern 2: capitalized class imported directly, e.g. GitHub README style
    try:
        from NaijaBet_Api.bookmakers import Bet9ja as _Bet9jaClass
        from NaijaBet_Api.id import Betid as _Betid
        Bet9jaClass = _Bet9jaClass
        Betid = _Betid
        _AVAILABLE = True
    except Exception as e2:
        _IMPORT_ERROR = f"Pattern 1 failed: {e1} | Pattern 2 failed: {e2}"


class Bet9jaServiceError(Exception):
    pass


LEAGUE_MAP = {
    "epl": "PREMIERLEAGUE",
    "premierleague": "PREMIERLEAGUE",
}


def get_bet9ja_odds(league: str = "epl"):
    if not _AVAILABLE:
        raise Bet9jaServiceError(
            f"NaijaBet_Api could not be imported. Details: {_IMPORT_ERROR}"
        )

    league_key = LEAGUE_MAP.get(league.lower())
    if not league_key:
        raise Bet9jaServiceError(
            f"Unknown league '{league}'. Supported: {', '.join(LEAGUE_MAP)}"
        )

    try:
        b9 = Bet9jaClass()
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
