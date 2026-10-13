"""
The owner's payment pages in a business's deposit settings: the live ones
a new deposit may use, and the page a deposit already asked was issued on,
which stays readable after the owner removed it (retired) until no hold
can still need it, so a waiting deposit keeps its link.
"""

from typed_time_provider import Microseconds

from app.schemas.domain.deposits import (
    DepositSettingsDocument,
    PaymentLink,
    RetiredPaymentLink,
)
from app.schemas.typings.deposits.prefixed_id import PaymentLinkId
from app.utilities.deposits.deposit_times import minutes_later

# No deposit waits longer than the longest hold the settings allow (a day,
# the upper bound of DepositHoldMinutes).
LONGEST_HOLD_MINUTES: int = 1440


def every_page(settings: DepositSettingsDocument) -> list[PaymentLink]:
    """The live pages, then the retired ones (all a key rotation reseals)."""

    return [
        *settings.payment_links,
        *(retired.link for retired in settings.retired_payment_links),
    ]


def issued_page(
    settings: DepositSettingsDocument | None, link_id: PaymentLinkId
) -> PaymentLink | None:
    """The page a deposit was asked on, live or retired; None once it is gone."""

    if settings is None:
        return None

    return next((link for link in every_page(settings) if link.id == link_id), None)


def retire_page(
    settings: DepositSettingsDocument, link_id: PaymentLinkId, now: Microseconds
) -> bool:
    """
    Take a live page out of the owner's list and keep it for the deposits
    already asked on it; pages retired longer ago than the longest hold go
    for good. False when no live page has the id.
    """

    page: PaymentLink | None = next(
        (link for link in settings.payment_links if link.id == link_id), None
    )
    if page is None:
        return False

    settings.payment_links = [
        link for link in settings.payment_links if link.id != link_id
    ]
    settings.retired_payment_links = [
        *(
            retired
            for retired in settings.retired_payment_links
            if int(minutes_later(retired.retired_at, LONGEST_HOLD_MINUTES)) > int(now)
        ),
        RetiredPaymentLink(link=page, retired_at=now),
    ]
    return True
