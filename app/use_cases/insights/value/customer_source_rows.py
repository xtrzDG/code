"""
The rows of the customer sources report, folded from grouped counts: one
per source tag, one per channel for conversations without a tag, and the
smallest tags together when there are many (a link anyone can retag).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.value import CustomerSourceKind, ValueBasis
from app.schemas.dto.value.customer_sources import (
    ConversationBookingCount,
    ConversationLeadCount,
    ConversationOrigin,
    CustomerSourceRow,
    SourceConversationCount,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from app.schemas.typings.value.constrained_integers import (
    AverageCheckMinor,
    BookedValueMinor,
)
from app.use_cases.insights.dashboard_values import EARNING_STATUSES
from app.use_cases.insights.value.value_money import (
    BookedMoney,
    MoneyEstimate,
    estimate_money,
)

# Tags shown one by one; the others are folded into one row.
MAX_TAGGED_ROWS: int = 20

# A row's key: its tag, else the channel of its untagged conversations.
type RowKey = tuple[AcquisitionSourceTag | None, ChannelKind | None]


@dataclass
class RowTally:
    """What one row counted so far."""

    kind: CustomerSourceKind
    source: AcquisitionSourceTag | None = None
    channels: set[ChannelKind] = field(default_factory=set[ChannelKind])
    source_count: int = 1
    conversations: int = 0
    bookings: int = 0
    valued_bookings: int = 0
    booked_value: int = 0
    requests: int = 0

    def add(self, other: RowTally) -> None:
        self.channels |= other.channels
        self.conversations += other.conversations
        self.bookings += other.bookings
        self.valued_bookings += other.valued_bookings
        self.booked_value += other.booked_value
        self.requests += other.requests


@dataclass(frozen=True)
class SourcePricing:
    """How the bookings and requests of a row are priced."""

    basis: ValueBasis
    average_check: AverageCheckMinor | None


def row_key(source: AcquisitionSourceTag | None, channel: ChannelKind) -> RowKey:
    return (source, None) if source is not None else (None, channel)


def tally_rows(
    conversations: Sequence[SourceConversationCount],
    bookings: Sequence[ConversationBookingCount],
    leads: Sequence[ConversationLeadCount],
    origins: Sequence[ConversationOrigin],
    currency_code: CurrencyCode,
) -> list[RowTally]:
    """
    The rows of the period: conversations by their own source; bookings
    and requests by the source of their conversation (one not found, an
    erased one, is left out). Only kept bookings count; a value counts in
    the business currency only.
    """

    rows: dict[RowKey, RowTally] = {}

    def row_of(source: AcquisitionSourceTag | None, channel: ChannelKind) -> RowTally:
        key: RowKey = row_key(source, channel)
        if key not in rows:
            rows[key] = RowTally(
                kind=CustomerSourceKind.UNTAGGED
                if source is None
                else CustomerSourceKind.TAGGED,
                source=source,
            )

        row: RowTally = rows[key]
        row.channels.add(channel)
        return row

    for counted in conversations:
        row_of(counted.acquisition_source, counted.channel).conversations += int(
            counted.count
        )

    origin_of: dict[ConversationId, ConversationOrigin] = {
        origin.conversation_id: origin for origin in origins
    }
    for booking in bookings:
        origin: ConversationOrigin | None = origin_of.get(booking.conversation_id)
        if origin is None or booking.status not in EARNING_STATUSES:
            continue

        row: RowTally = row_of(origin.acquisition_source, origin.channel)
        row.bookings += int(booking.count)
        if booking.currency_code == currency_code:
            row.valued_bookings += int(booking.count)
            row.booked_value += int(booking.value_minor)

    for lead in leads:
        lead_origin: ConversationOrigin | None = origin_of.get(lead.conversation_id)
        if lead_origin is not None:
            row_of(lead_origin.acquisition_source, lead_origin.channel).requests += int(
                lead.count
            )

    return list(rows.values())


def build_source_rows(
    tallies: Iterable[RowTally],
    pricing: SourcePricing,
) -> list[CustomerSourceRow]:
    """Most conversations first; tags past `MAX_TAGGED_ROWS` folded together."""

    ordered: list[RowTally] = sorted(tallies, key=row_order)
    tagged: list[RowTally] = [
        row for row in ordered if row.kind is CustomerSourceKind.TAGGED
    ]
    folded: list[RowTally] = tagged[MAX_TAGGED_ROWS:]
    folded_ids: set[int] = {id(row) for row in folded}
    shown: list[RowTally] = [row for row in ordered if id(row) not in folded_ids]
    if folded:
        rest: RowTally = RowTally(
            kind=CustomerSourceKind.OTHER, source_count=len(folded)
        )
        for row in folded:
            rest.add(row)

        shown.append(rest)

    return [to_row(row, pricing) for row in shown]


def row_order(row: RowTally) -> tuple[int, int, int, str]:
    label: str = str(row.source or "") + ",".join(sorted(row.channels))
    return (-row.conversations, -row.bookings, -row.requests, label)


def to_row(row: RowTally, pricing: SourcePricing) -> CustomerSourceRow:
    earning_units: int = (
        row.bookings if pricing.basis is ValueBasis.BOOKINGS else row.requests
    )
    money: MoneyEstimate = estimate_money(
        pricing.basis,
        earning_units,
        BookedMoney(
            count=PeriodItemCount(row.valued_bookings),
            value_minor=BookedValueMinor(row.booked_value),
        ),
        pricing.average_check,
    )
    return CustomerSourceRow(
        kind=row.kind,
        acquisition_source=row.source,
        channels=sorted(row.channels),
        source_count=PeriodItemCount(row.source_count),
        conversation_count=PeriodItemCount(row.conversations),
        booking_count=PeriodItemCount(row.bookings),
        request_count=PeriodItemCount(row.requests),
        estimated_value_minor=money.estimated_revenue_minor,
    )
