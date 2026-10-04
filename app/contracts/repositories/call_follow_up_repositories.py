"""
Persistence contracts of what follows a phone call: the callers who did not
get through (and the messages they got), and each business's call
settings. Every read is limited to one business.
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount

type MissedCallChange = Callable[[MissedCallDocument], MissedCallDocument | None]


class MissedCallRepoContract(RepoContract, Protocol):
    def insert_if_new(self, missed_call: MissedCallDocument) -> IsDocumentInserted:
        """
        Store a missed call unless one with its id exists (atomic, also
        across processes); True when it was stored now.
        """
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        missed_call_id: MissedCallId,
    ) -> MissedCallDocument | None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        missed_call_id: MissedCallId,
        change: MissedCallChange,
    ) -> MissedCallDocument | None:
        """
        Store what `change` makes of the missed call as stored now; None,
        and nothing written, when it is gone or `change` returns None.
        """
        raise NotImplementedError

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
    ) -> list[MissedCallDocument]:
        """One keyset page of the business's missed calls, newest first."""
        raise NotImplementedError

    def list_by_caller(
        self,
        business_id: BusinessId,
        caller_phone_number: E164PhoneNumber,
    ) -> list[MissedCallDocument]:
        """The business's missed calls from one number, oldest first."""
        raise NotImplementedError

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        """Remove every business's missed calls stored before then (retention)."""
        raise NotImplementedError


class CallSettingsRepoContract(RepoContract, Protocol):
    def get_by_business(self, business_id: BusinessId) -> CallSettingsDocument | None:
        raise NotImplementedError

    def save(self, settings: CallSettingsDocument) -> None:
        raise NotImplementedError
