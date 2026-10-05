"""Customers → Segments: saved groups of customers, their members and CSV."""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.dto.contacts import ContactSummaryView
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.booleans import IsSegmentCountExact, IsVipOnlySegment
from app.schemas.typings.contacts.constrained_integers import (
    SegmentBookingCount,
    SegmentInactivityDays,
    SegmentMemberCount,
)
from app.schemas.typings.contacts.constrained_strings import CustomerTag, SegmentName
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.users.prefixed_id import UserId


class SegmentRulesBody(ImmutableDTO):
    """
    Who belongs to a segment (every rule given must hold): a tag, the
    latest visit more than N days ago, at least / at most so many bookings,
    VIPs only. Blocked and erased customers never belong.
    """

    tag: CustomerTag | None = None
    last_visit_days_ago: SegmentInactivityDays | None = None
    min_bookings: SegmentBookingCount | None = None
    max_bookings: SegmentBookingCount | None = None
    vip_only: IsVipOnlySegment = False

    @model_validator(mode="after")
    def bounds_in_order(self) -> Self:
        if (
            self.min_bookings is not None
            and self.max_bookings is not None
            and int(self.min_bookings) > int(self.max_bookings)
        ):
            raise ValueError("min_bookings must not exceed max_bookings.")

        return self


class SegmentRequest(ImmutableDTO):
    """A segment as the owner names and defines it."""

    name: SegmentName
    rules: SegmentRulesBody = Field(default_factory=SegmentRulesBody)


class SegmentListQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class CreateSegmentCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: SegmentRequest
    client_ip_address: ClientIpAddress | None = None


class UpdateSegmentCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    segment_id: CustomerSegmentId
    request: SegmentRequest
    client_ip_address: ClientIpAddress | None = None


class SegmentQuery(ImmutableDTO):
    """One segment (to delete it)."""

    user_id: UserId
    business_id: BusinessId
    segment_id: CustomerSegmentId
    client_ip_address: ClientIpAddress | None = None


class SegmentView(ImmutableDTO):
    id: CustomerSegmentId
    name: SegmentName
    rules: SegmentRulesBody
    created_at: Microseconds
    updated_at: Microseconds


class SegmentList(ImmutableDTO):
    """The business's segments, the oldest first, and its tags to build one with."""

    items: list[SegmentView] = Field(default_factory=list[SegmentView])
    known_tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])


class SegmentMembersQuery(ImmutableDTO):
    """One page of a saved segment's members, the most recently active first."""

    user_id: UserId
    business_id: BusinessId
    segment_id: CustomerSegmentId
    page: PageRequest = PageRequest()
    client_ip_address: ClientIpAddress | None = None


class SegmentPreviewCommand(ImmutableDTO):
    """How many customers rules would hold, before the owner saves them."""

    user_id: UserId
    business_id: BusinessId
    rules: SegmentRulesBody
    client_ip_address: ClientIpAddress | None = None


class SegmentPreview(ImmutableDTO):
    """
    How many customers belong (`is_count_exact` False when the business
    has more customers than one count reads: then "at least"), and the
    first few of them.
    """

    member_count: SegmentMemberCount
    is_count_exact: IsSegmentCountExact
    sample: list[ContactSummaryView] = Field(default_factory=list[ContactSummaryView])


class StartSegmentExportCommand(ImmutableDTO):
    """The owner downloads a segment's members as CSV (headings in `language`)."""

    user_id: UserId
    business_id: BusinessId
    segment_id: CustomerSegmentId
    language: LanguageTag
    client_ip_address: ClientIpAddress | None = None


class SegmentExportPageQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    segment_id: CustomerSegmentId
    cursor: PageCursor | None = None
