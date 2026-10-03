"""Notification links: the cabinet address of a signed token."""

from typed_time_provider import Microseconds

from app.contracts.notification_utilities import StaffLinkSignerContract
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.notifications.constrained_strings import CabinetDeepLink
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

# How long a notification link opens its page (after sign-in).
LINK_LIFETIME_MICROSECONDS: int = 7 * 24 * 60 * 60 * 1_000_000
LINK_PATH: str = "/n/"


def link_expiry(now: Microseconds) -> Microseconds:
    return Microseconds(int(now) + LINK_LIFETIME_MICROSECONDS)


def build_cabinet_link(
    signer: StaffLinkSignerContract,
    cabinet_base_url: CabinetBaseUrl | None,
    claims: StaffLinkClaims,
) -> CabinetDeepLink | None:
    """`{CABINET_BASE_URL}/n/{token}`; None when the cabinet's address is unknown."""

    if cabinet_base_url is None:
        return None

    token = signer.sign(claims)
    return CabinetDeepLink(f"{str(cabinet_base_url).rstrip('/')}{LINK_PATH}{token}")
