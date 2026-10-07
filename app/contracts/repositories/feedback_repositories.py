"""
Persistence contracts of the feedback after visits: each business's review
settings and the request for feedback after each visit. Every read is
limited to one business, except the two that run before a business is
known: the businesses that ask (the periodic job) and a review link by its
public token.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.contracts.repositories.business_document_pages import (
    BusinessDocumentPagesContract,
)
from app.schemas.domain.feedback import FeedbackRequestDocument, ReviewSettingsDocument
from app.schemas.dto.feedback.feedback_tallies import FeedbackTally
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.feedback.prefixed_id import FeedbackRequestId
from app.schemas.typings.storage.booleans import IsDocumentInserted

type FeedbackRequestChange = Callable[
    [FeedbackRequestDocument], FeedbackRequestDocument | None
]


class ReviewSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> ReviewSettingsDocument | None:
        raise NotImplementedError

    def save(self, settings: ReviewSettingsDocument) -> None:
        raise NotImplementedError

    def list_enabled(self) -> list[ReviewSettingsDocument]:
        """The settings of every business that asks for feedback (indexed)."""
        raise NotImplementedError


class FeedbackRequestRepoContract(
    BusinessDocumentPagesContract[FeedbackRequestDocument], RepoContract, Protocol
):
    def insert_if_new(self, request: FeedbackRequestDocument) -> IsDocumentInserted:
        """
        Store a request unless one with its id exists (atomic, also across
        processes); True when it was stored now.
        """
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        request_id: FeedbackRequestId,
    ) -> FeedbackRequestDocument | None:
        raise NotImplementedError

    def get_many(
        self,
        business_id: BusinessId,
        request_ids: Sequence[FeedbackRequestId],
    ) -> dict[FeedbackRequestId, FeedbackRequestDocument]:
        """The business's requests of these ids in one read."""
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        request_id: FeedbackRequestId,
        change: FeedbackRequestChange,
    ) -> FeedbackRequestDocument | None:
        """
        Store what `change` makes of the request as stored now, in one
        step; None, and nothing written, when it is gone, belongs to
        another business, or `change` returns None.
        """
        raise NotImplementedError

    def list_waiting(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> list[FeedbackRequestDocument]:
        """The customer's SENT requests (waiting for a rating), newest first."""
        raise NotImplementedError

    def list_by_contact(
        self,
        business_id: BusinessId,
        contact_id: ContactId,
    ) -> list[FeedbackRequestDocument]:
        """Every request about the customer's visits, oldest first."""
        raise NotImplementedError

    def find_by_token(self, token: ReviewLinkToken) -> FeedbackRequestDocument | None:
        """
        The request whose review link carries this token, in any business
        (the caller lifts the storage scope explicitly).
        """
        raise NotImplementedError

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
    ) -> list[FeedbackRequestDocument]:
        """One keyset page of the business's requests, newest first."""
        raise NotImplementedError

    def tally(
        self,
        business_id: BusinessId,
        created_from: Microseconds,
    ) -> FeedbackTally:
        """The requests created since then, counted in the database."""
        raise NotImplementedError
