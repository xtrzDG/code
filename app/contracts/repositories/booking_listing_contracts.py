"""
Keyset pages and database counts of bookings, leads, handoffs and
unanswered questions (the cabinet's lists and the dashboard). Pages read
the page size plus one item after the window's position; counts never
read documents into the application.
"""

from typing import Protocol

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.handoffs import HandoffStatus, HandoffUrgency
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.dto.listing_filters import BookingListFilter, HandoffListFilter
from app.schemas.dto.operations.activity_counts import (
    ActivityPeriod,
    BookingActivityCount,
    BookingValueCount,
    HandoffActivityCount,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.bookings.booleans import IsSandboxIncluded
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.handoffs.booleans import IsResolvedIncluded
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.platform.constrained_integers import ListItemCount


class BookingListingContract(Protocol):
    def page_by_business(
        self, business_id: BusinessId, window: KeysetSlice, listing: BookingListFilter
    ) -> list[BookingDocument]:
        """By start time in the filter's order, ties in write order."""
        raise NotImplementedError

    def list_ending_after(
        self, business_id: BusinessId, moment: BookingSearchBoundSeconds
    ) -> list[BookingDocument]:
        """Bookings not over at `moment`, by start time (availability)."""
        raise NotImplementedError

    def list_ending_between(
        self,
        business_id: BusinessId,
        ended_after: BookingSearchBoundSeconds,
        ended_by: BookingSearchBoundSeconds,
    ) -> list[BookingDocument]:
        """
        Bookings that ended after `ended_after` and by `ended_by`, by end
        time (the visits to ask about).
        """
        raise NotImplementedError

    def list_by_conversation(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> list[BookingDocument]:
        raise NotImplementedError

    def count_made(
        self, business_id: BusinessId, period: ActivityPeriod
    ) -> list[BookingActivityCount]:
        """Bookings made in the period per status and segment, no sandbox."""
        raise NotImplementedError

    def sum_value_made(
        self,
        business_id: BusinessId,
        period: ActivityPeriod,
        by_staff_only: bool = False,
    ) -> list[BookingValueCount]:
        """
        Bookings made in the period per status, currency and segment with
        their summed values, no sandbox (summed by the database); with
        `by_staff_only` only those made outside any conversation.
        """
        raise NotImplementedError


class LeadListingContract(Protocol):
    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        status: LeadStatus | None,
        include_sandbox: IsSandboxIncluded,
    ) -> list[LeadDocument]:
        """Newest first, ties in write order."""
        raise NotImplementedError

    def count_by_status(
        self, business_id: BusinessId, include_sandbox: IsSandboxIncluded
    ) -> dict[LeadStatus, ListItemCount]:
        raise NotImplementedError

    def count_made(
        self, business_id: BusinessId, start: Microseconds, end: Microseconds
    ) -> PeriodItemCount:
        """Leads made in the period, no sandbox."""
        raise NotImplementedError

    def list_by_conversation(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> list[LeadDocument]:
        raise NotImplementedError


class HandoffListingContract(Protocol):
    def page_open(
        self,
        business_id: BusinessId,
        urgency: HandoffUrgency,
        window: KeysetSlice,
        listing: HandoffListFilter,
    ) -> list[HandoffDocument]:
        """Open handoffs of one urgency, the oldest first."""
        raise NotImplementedError

    def page_resolved(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        include_sandbox: IsSandboxIncluded,
    ) -> list[HandoffDocument]:
        """Resolved handoffs, the most recently resolved first."""
        raise NotImplementedError

    def count_by_status(
        self, business_id: BusinessId, include_sandbox: IsSandboxIncluded
    ) -> dict[HandoffStatus, ListItemCount]:
        raise NotImplementedError

    def count_made(
        self, business_id: BusinessId, period: ActivityPeriod
    ) -> list[HandoffActivityCount]:
        """Handoffs made in the period per reason, urgency and segment."""
        raise NotImplementedError

    def count_made_since(
        self, business_id: BusinessId, since: Microseconds
    ) -> PeriodItemCount:
        raise NotImplementedError

    def list_by_conversation(
        self, business_id: BusinessId, conversation_id: ConversationId
    ) -> list[HandoffDocument]:
        raise NotImplementedError


class UnansweredQuestionListingContract(Protocol):
    def page_by_rank(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        include_resolved: IsResolvedIncluded,
        include_sandbox: IsSandboxIncluded,
    ) -> list[UnansweredQuestionDocument]:
        """Most asked first, then the most recently asked, ties in write order."""
        raise NotImplementedError

    def count_open(self, business_id: BusinessId) -> ListItemCount:
        """Open questions outside the sandbox."""
        raise NotImplementedError
