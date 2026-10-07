from typed_time_provider import Microseconds

from app.contracts.repositories.call_follow_up_repositories import (
    CallSettingsRepoContract,
    MissedCallChange,
    MissedCallRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    ascending,
    field_equals,
    time_range,
)
from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.calls.call_follow_up_keys import call_settings_id_of

CALLER_PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("caller_phone_number")


class MissedCallRepository(
    BusinessScopedRepository[MissedCallDocument],
    MissedCallRepoContract,
):
    """
    Callers who did not get through, keyed by the id derived from the
    business, source and provider call id; pages newest first by
    `created_at` (indexed, migration 1051).
    """

    def insert_if_new(self, missed_call: MissedCallDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(missed_call.id), missed_call)

    def get(
        self,
        business_id: BusinessId,
        missed_call_id: MissedCallId,
    ) -> MissedCallDocument | None:
        return self._load(business_id, str(missed_call_id))

    def update(
        self,
        business_id: BusinessId,
        missed_call_id: MissedCallId,
        change: MissedCallChange,
    ) -> MissedCallDocument | None:
        return self._modify_in_business(business_id, str(missed_call_id), change)

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
    ) -> list[MissedCallDocument]:
        return self._page_in_business(business_id, (CREATED_AT_FIELD,), window)

    def list_by_caller(
        self,
        business_id: BusinessId,
        caller_phone_number: E164PhoneNumber,
    ) -> list[MissedCallDocument]:
        return self._list_in_business(
            business_id,
            (field_equals(CALLER_PHONE_NUMBER_FIELD, caller_phone_number),),
            order=ascending(CREATED_AT_FIELD),
        )

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, ending_before=created_before)
        )


class CallSettingsRepository(
    BusinessScopedRepository[CallSettingsDocument],
    CallSettingsRepoContract,
):
    """One settings document per business, keyed by the derived id."""

    def get_by_business(self, business_id: BusinessId) -> CallSettingsDocument | None:
        return self._load(business_id, str(call_settings_id_of(business_id)))

    def save(self, settings: CallSettingsDocument) -> None:
        self._store(str(settings.id), settings)
