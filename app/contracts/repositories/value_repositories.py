"""
Persistence contracts of what the assistant is worth to a business: the
average check, each owner's digest choices, the stored digests and monthly
reports, and the indexed counts the value model needs beyond the
dashboard's. Every read is limited to one business; sandbox activity (the
owner's test chat, autotests) is never counted.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.insights.constrained_integers import PeriodItemCount
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.prefixed_id import ValueReportId


class ValueSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> ValueSettingsDocument | None:
        raise NotImplementedError

    def save(self, settings: ValueSettingsDocument) -> None:
        raise NotImplementedError


class DigestPreferencesRepoContract(RepoContract, Protocol):
    def get(
        self,
        business_id: BusinessId,
        user_id: UserId,
    ) -> DigestPreferencesDocument | None:
        """One owner's choices in the business; None: the defaults."""
        raise NotImplementedError

    def save(self, preferences: DigestPreferencesDocument) -> None:
        raise NotImplementedError


class ValueReportRepoContract(RepoContract, Protocol):
    def get(
        self,
        business_id: BusinessId,
        report_id: ValueReportId,
    ) -> ValueReportDocument | None:
        raise NotImplementedError

    def insert_if_new(self, report: ValueReportDocument) -> IsDocumentInserted:
        """
        Store the report unless one of its period exists (atomic, also
        across processes); True when it was stored now.
        """
        raise NotImplementedError

    def page_by_business(
        self,
        business_id: BusinessId,
        kind: ValueReportKind,
        window: KeysetSlice,
    ) -> list[ValueReportDocument]:
        """One keyset page of the business's reports of a kind, newest period first."""
        raise NotImplementedError


class ValueCountRepoContract(RepoContract, Protocol):
    def count_bookings_made_by_staff(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
    ) -> dict[BookingStatus, PeriodItemCount]:
        """
        Bookings made from `start` to `end` (created) outside any
        conversation (staff added them in the cabinet), by status.
        """
        raise NotImplementedError

    def count_assistant_replies(
        self,
        business_id: BusinessId,
        start: Microseconds,
        end: Microseconds,
        conversation_ids: Sequence[ConversationId] | None = None,
    ) -> PeriodItemCount:
        """Messages the assistant wrote from `start` to `end` (in these chats)."""
        raise NotImplementedError

    def count_bookings_starting(
        self,
        business_id: BusinessId,
        starts_from: BookingSearchBoundSeconds,
        starts_before: BookingSearchBoundSeconds,
    ) -> dict[BookingStatus, PeriodItemCount]:
        """Bookings that start from `starts_from` to `starts_before`, by status."""
        raise NotImplementedError
