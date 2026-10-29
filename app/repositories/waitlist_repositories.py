from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.waitlist_repositories import (
    WaitlistEntryChange,
    WaitlistEntryRepoContract,
    WaitlistSettingsRepoContract,
)
from app.repositories.aggregate_reading import parse_choice
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    ascending,
    field_among,
    field_equals,
    time_range,
    without_sandbox,
)
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument
from app.schemas.dto.growth.growth_counts import WaitlistStatusCount
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_aggregates import DocumentAggregation, DocumentGroupCount
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.waitlist.constrained_integers import WaitlistEntryCount
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId
from app.utilities.waitlist.waitlist_keys import waitlist_settings_id_of

CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
OFFER_EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("offer_expires_at")
WAITS_UNTIL_FIELD: DocumentFieldPath = DocumentFieldPath("waits_until")


class WaitlistSettingsRepository(
    BusinessScopedRepository[WaitlistSettingsDocument],
    WaitlistSettingsRepoContract,
):
    """One settings document per business, keyed by the derived id."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> WaitlistSettingsDocument | None:
        return self._load(business_id, str(waitlist_settings_id_of(business_id)))

    def save(self, settings: WaitlistSettingsDocument) -> None:
        self._store(str(settings.id), settings)


class WaitlistEntryRepository(
    BusinessScopedRepository[WaitlistEntryDocument],
    WaitlistEntryRepoContract,
):
    """
    Waitlist entries, read by business and id, by customer, by status in
    join order (indexed, migration 1151) and, across businesses for the
    sweep, by status with the end of a hold or of the wanted day.
    """

    def save(self, entry: WaitlistEntryDocument) -> None:
        self._store(str(entry.id), entry)

    def get(
        self, business_id: BusinessId, entry_id: WaitlistEntryId
    ) -> WaitlistEntryDocument | None:
        return self._load(business_id, str(entry_id))

    def update(
        self,
        business_id: BusinessId,
        entry_id: WaitlistEntryId,
        change: WaitlistEntryChange,
    ) -> WaitlistEntryDocument | None:
        return self._modify_in_business(business_id, str(entry_id), change)

    def list_of_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> list[WaitlistEntryDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(CONTACT_ID_FIELD, contact_id)],
            order=ascending(CREATED_AT_FIELD),
        )

    def list_in_status(
        self,
        business_id: BusinessId,
        status: WaitlistStatus,
        limit: DocumentQueryLimit,
    ) -> list[WaitlistEntryDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(STATUS_FIELD, status)],
            order=ascending(CREATED_AT_FIELD),
            limit=limit,
        )

    def page_in_statuses(
        self,
        business_id: BusinessId,
        statuses: Sequence[WaitlistStatus],
        window: KeysetSlice,
        is_descending: bool,
    ) -> list[WaitlistEntryDocument]:
        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            where=DocumentFilter(
                among=(field_among(STATUS_FIELD, statuses),),
                excluding=(without_sandbox(),),
            ),
            is_descending=is_descending,
        )

    def count_by_status(self, business_id: BusinessId) -> list[WaitlistStatusCount]:
        groups: list[DocumentGroupCount] = self._aggregate_in_business(
            business_id,
            DocumentAggregation(
                where=DocumentFilter(excluding=(without_sandbox(),)),
                group_by=(STATUS_FIELD,),
            ),
        )
        return [
            WaitlistStatusCount(
                status=status, count=WaitlistEntryCount(int(group.count))
            )
            for group in groups
            if (status := parse_choice(WaitlistStatus, group.values[0])) is not None
        ]

    def list_lapsed_offers(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[WaitlistEntryDocument]:
        return self._collection.list_by_range(
            time_range(
                OFFER_EXPIRES_AT_FIELD, ending_before=Microseconds(int(now) + 1)
            ),
            (field_equals(STATUS_FIELD, WaitlistStatus.OFFERED),),
            limit=limit,
        )

    def list_past_waiting(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[WaitlistEntryDocument]:
        return self._collection.list_by_range(
            time_range(WAITS_UNTIL_FIELD, ending_before=Microseconds(int(now) + 1)),
            (field_equals(STATUS_FIELD, WaitlistStatus.WAITING),),
            limit=limit,
        )
