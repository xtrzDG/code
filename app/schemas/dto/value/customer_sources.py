"""
Where a business's customers came from in a period (Reports, "Where
customers came from"): conversations, bookings and value per source.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.value import CustomerSourceKind, ValueBasis, ValuePeriod
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_integers import (
    BookedValueMinor,
    EstimatedRevenueMinor,
)


class SourceConversationCount(ImmutableDTO):
    """Conversations started in a period with one source on one channel."""

    acquisition_source: AcquisitionSourceTag | None = None
    channel: ChannelKind
    count: PeriodItemCount


class ConversationBookingCount(ImmutableDTO):
    """
    Bookings made in a period in one conversation, with one status and
    currency (None: without a value), and what they are worth together.
    """

    conversation_id: ConversationId
    status: BookingStatus
    currency_code: CurrencyCode | None = None
    count: PeriodItemCount
    value_minor: BookedValueMinor


class ConversationLeadCount(ImmutableDTO):
    """Requests taken in a period in one conversation."""

    conversation_id: ConversationId
    count: PeriodItemCount


class ConversationOrigin(ImmutableDTO):
    """Where one conversation came from: its source and its channel."""

    conversation_id: ConversationId
    acquisition_source: AcquisitionSourceTag | None = None
    channel: ChannelKind


class CustomerSourcesQuery(ImmutableDTO):
    """
    The sources of a period for an owner: a named period, or local dates
    `date_from` to `date_to` (inclusive, at most 366 days); neither: the
    last 30 days.
    """

    user_id: UserId
    business_id: BusinessId
    period: ValuePeriod | None = None
    date_from: LocalDate | None = None
    date_to: LocalDate | None = None


class CustomerSourceRow(ImmutableDTO):
    """
    One source of the period: a tag (`TAGGED`, every channel it came
    through), the conversations of one channel without a tag (`UNTAGGED`),
    or the smallest tags folded together (`OTHER`).

    `booking_count`: bookings made in the period in the source's
    conversations and kept (not cancelled, not a no-show), whenever those
    conversations started; `request_count`: requests taken in them;
    `estimated_value_minor`: their value as the value model counts it (own
    values, the others at the average check; requests at the check), None
    when nothing prices them.
    """

    kind: CustomerSourceKind
    acquisition_source: AcquisitionSourceTag | None = None
    channels: list[ChannelKind] = Field(default_factory=list[ChannelKind])
    source_count: PeriodItemCount = PeriodItemCount(1)
    conversation_count: PeriodItemCount
    booking_count: PeriodItemCount
    request_count: PeriodItemCount
    estimated_value_minor: EstimatedRevenueMinor | None = None


class CustomerSourcesView(ImmutableDTO):
    """The sources of a period, most conversations first."""

    business_id: BusinessId
    currency_code: CurrencyCode
    date_from: LocalDate
    date_to: LocalDate
    value_basis: ValueBasis
    rows: list[CustomerSourceRow] = Field(default_factory=list[CustomerSourceRow])
