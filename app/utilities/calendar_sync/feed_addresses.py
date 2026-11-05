"""
Addresses of imported calendar feeds: what is read (webcal is https), the
host the cabinet shows instead of the secret address, and what is accepted.
"""

from urllib.parse import urlsplit

from app.schemas.typings.calendar_sync.constrained_strings import (
    CalendarFeedHost,
    CalendarFeedUrl,
)
from app.schemas.typings.web_fetching.constrained_integers import WebFetchByteLimit
from app.schemas.typings.web_fetching.constrained_strings import (
    WebMediaType,
    WebResourceUrl,
)

WEBCAL_SCHEME: str = "webcal://"
# Feeds are served as text/calendar, but many hosts send them as plain
# text or bytes; the parser decides whether it is a calendar.
ICAL_MEDIA_TYPES: frozenset[WebMediaType] = frozenset(
    WebMediaType(kind)
    for kind in (
        "text/calendar",
        "text/plain",
        "application/ics",
        "application/x-ics",
        "text/x-vcalendar",
        "application/octet-stream",
    )
)
# A year of a busy rental is a few hundred KB; 4 MB is plenty.
ICAL_FEED_BYTE_LIMIT: WebFetchByteLimit = WebFetchByteLimit(4 * 1024 * 1024)


def fetchable_feed_url(address: str) -> WebResourceUrl:
    """The address to fetch: webcal:// is https://; anything else as given."""

    text: str = address.strip()
    if text.lower().startswith(WEBCAL_SCHEME):
        text = "https://" + text[len(WEBCAL_SCHEME) :]

    return WebResourceUrl(text)


def feed_host(url: CalendarFeedUrl) -> CalendarFeedHost:
    """The host of a feed address (lower case), shown instead of the address."""

    host: str = urlsplit(str(fetchable_feed_url(str(url)))).hostname or ""
    return CalendarFeedHost(host.lower())
