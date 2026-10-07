"""Counts of the waitlist's and the campaigns' work, as the database groups them."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.bookings import BookingOrigin, BookingStatus
from app.schemas.constants.campaigns import CampaignMessageStatus
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.typings.campaigns.constrained_integers import CampaignMessageCount
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.value.constrained_integers import BookedValueMinor
from app.schemas.typings.waitlist.constrained_integers import WaitlistEntryCount


class OriginBookingCount(ImmutableDTO):
    """
    The bookings of one origin (waitlist, campaign) made in a period in one
    status and currency, with their summed values (sandbox left out).
    """

    origin: BookingOrigin
    status: BookingStatus
    currency_code: CurrencyCode | None = None
    count: PeriodItemCount
    value_minor: BookedValueMinor


class WaitlistStatusCount(ImmutableDTO):
    """How many of a business's (real) waitlist entries are in one status."""

    status: WaitlistStatus
    count: WaitlistEntryCount


class CampaignStatusCount(ImmutableDTO):
    """How many of a business's campaign messages of a period are in one status."""

    status: CampaignMessageStatus
    count: CampaignMessageCount
