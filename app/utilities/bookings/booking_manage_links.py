"""
A guest's links about their booking: the manage page (`/r/{token}` on the
cabinet's site), how long it opens, and the map of the business's address.
"""

from urllib.parse import quote

from typed_time_provider import Microseconds

from app.schemas.domain.profiles import BusinessAddress
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
)
from app.schemas.typings.bookings.constrained_strings import (
    BookingManageLink,
    BookingManageToken,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

MANAGE_LINK_PATH: str = "/r/"
# A link opens the booking's page until a month after it ends (the guest
# may still want its details, an .ics file or a way to write).
LINK_DAYS_AFTER_END: int = 30
SECONDS_PER_DAY: int = 24 * 60 * 60
MICROSECONDS_PER_SECOND: int = 1_000_000
# Google's documented cross-platform Maps URL (search by text): it opens
# the maps app on phones and the web anywhere else.
MAPS_SEARCH_URL: str = "https://www.google.com/maps/search/?api=1&query="


def manage_link_expiry(ends_at: BookingEndsAtUnixSeconds) -> Microseconds:
    """When a manage link of a booking ending at `ends_at` stops opening."""

    expires_seconds: int = int(ends_at) + LINK_DAYS_AFTER_END * SECONDS_PER_DAY
    return Microseconds(expires_seconds * MICROSECONDS_PER_SECOND)


def build_manage_link(
    cabinet_base_url: CabinetBaseUrl | None,
    token: BookingManageToken,
) -> BookingManageLink | None:
    """`{CABINET_BASE_URL}/r/{token}`; None while the cabinet's address is unknown."""

    if cabinet_base_url is None:
        return None

    return BookingManageLink(
        f"{str(cabinet_base_url).rstrip('/')}{MANAGE_LINK_PATH}{token}"
    )


def choose_maps_url(address: BusinessAddress | None) -> WebLink | None:
    """
    The owner's maps link of the address, else a maps search of the address
    text; None without an address.
    """

    if address is None:
        return None

    if address.maps_url is not None:
        return address.maps_url

    text: str = " ".join(str(address.text).split())
    if not text:
        return None

    return WebLink(MAPS_SEARCH_URL + quote(text, safe=""))
