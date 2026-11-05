"""
A server-side fetch the SSRF guard refused, as a security event: a link,
redirect hop, calendar feed or webhook address that is not a public https
address (a private or metadata IP, an intranet name, credentials in it, a
port other than 80/443, another scheme). The line names the refusal and
the target host only, never the path or query (an ICS feed's secret lives
there); who asked is only the pseudonymous actor every security line
carries (`security_events.py`).
"""

from urllib.parse import urlsplit

from app.schemas.constants.web_fetching import REFUSED_FETCH_PROBLEMS
from app.schemas.exceptions.web_fetch_errors import WebFetchError
from app.utilities.observability.security_events import (
    OUTBOUND_FETCH_REFUSED,
    log_security_event,
)

# Where the line says the refusal happened (no route: it is outbound).
OUTBOUND_PATH: str = "outbound"
MAX_LOGGED_HOST_LENGTH: int = 253
LOGGED_HOST_CHARACTERS: frozenset[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789.-:[]_"
)


def log_refused_fetch(error: WebFetchError, url: str, purpose: str) -> None:
    """One `outbound_fetch_refused` line when `error` is a guard refusal."""

    if error.problem not in REFUSED_FETCH_PROBLEMS:
        return

    log_security_event(
        OUTBOUND_FETCH_REFUSED,
        path=OUTBOUND_PATH,
        reason=error.problem.value,
        client_address=None,
        purpose=purpose,
        target_host=logged_host(url),
    )


def logged_host(url: str) -> str:
    """The address's host, lower case, without anything a log must not hold."""

    try:
        host: str = urlsplit(url.strip()).hostname or ""
    except ValueError:
        host = ""

    cleaned: str = "".join(
        character for character in host.lower() if character in LOGGED_HOST_CHARACTERS
    )
    return cleaned[:MAX_LOGGED_HOST_LENGTH] or "unknown"
