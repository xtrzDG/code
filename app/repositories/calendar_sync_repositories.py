"""
Repositories of two-way availability (1160): the calendar settings of each
resource, the busy times of each of its sources, and its export feeds.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.calendar_sync import (
    CalendarBusyTimesRepoContract,
    CalendarLinkChange,
    IcalExportFeedRepoContract,
    ResourceCalendarLinkRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import time_range
from app.schemas.domain.calendar_sync import (
    CalendarBusyTimesDocument,
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_strings import IcalExportTokenHash
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.utilities.calendar_sync.calendar_sync_keys import (
    resource_calendar_link_id_of,
)

NEXT_SYNC_AT_FIELD: DocumentFieldPath = DocumentFieldPath("next_sync_at")


class ResourceCalendarLinkRepository(
    BusinessScopedRepository[ResourceCalendarLinkDocument],
    ResourceCalendarLinkRepoContract,
):
    """
    One document per resource, keyed by its derived id; the sync job finds
    the due ones across businesses by `next_sync_at` (indexed, 1160).
    """

    def get(
        self, business_id: BusinessId, resource_id: ResourceId
    ) -> ResourceCalendarLinkDocument | None:
        return self._load(business_id, str(resource_calendar_link_id_of(resource_id)))

    def add(self, link: ResourceCalendarLinkDocument) -> None:
        self._collection.insert_if_absent(str(link.id), link)

    def update(
        self,
        business_id: BusinessId,
        resource_id: ResourceId,
        change: CalendarLinkChange,
    ) -> ResourceCalendarLinkDocument | None:
        def change_own(
            stored: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument | None:
            return change(stored) if stored.business_id == business_id else None

        return self._collection.modify(
            str(resource_calendar_link_id_of(resource_id)), change_own
        )

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[ResourceCalendarLinkDocument]:
        return self._list_in_business(business_id)

    def list_due(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[ResourceCalendarLinkDocument]:
        return self._collection.list_by_range(
            time_range(NEXT_SYNC_AT_FIELD, ending_before=Microseconds(int(now) + 1)),
            limit=limit,
        )


class CalendarBusyTimesRepository(
    BusinessScopedRepository[CalendarBusyTimesDocument],
    CalendarBusyTimesRepoContract,
):
    """
    One document per resource and source, keyed by its derived id; a
    placement reads every one of the business (a few per resource).
    """

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[CalendarBusyTimesDocument]:
        return self._list_in_business(business_id)

    def store_if_newer(self, busy_times: CalendarBusyTimesDocument) -> bool:
        key: str = str(busy_times.id)
        if self._collection.insert_if_absent(key, busy_times):
            return True

        def replace_older(
            stored: CalendarBusyTimesDocument,
        ) -> CalendarBusyTimesDocument | None:
            if stored.business_id != busy_times.business_id or int(
                stored.fetched_at
            ) > int(busy_times.fetched_at):
                return None

            return busy_times.model_copy(update={"created_at": stored.created_at})

        return self._collection.modify(key, replace_older) is not None

    def delete(self, business_id: BusinessId, busy_times_ids: Sequence[str]) -> None:
        for busy_times_id in busy_times_ids:
            if self._load(business_id, busy_times_id) is not None:
                self._collection.delete(busy_times_id)


class IcalExportFeedRepository(
    BusinessScopedRepository[IcalExportFeedDocument],
    IcalExportFeedRepoContract,
):
    """Export feeds keyed by the hash of their token (the address's secret)."""

    def add(self, feed: IcalExportFeedDocument) -> None:
        self._collection.insert_if_absent(str(feed.token_hash), feed)

    def find(self, token_hash: IcalExportTokenHash) -> IcalExportFeedDocument | None:
        return self._collection.get(str(token_hash))

    def remove(self, business_id: BusinessId, token_hash: IcalExportTokenHash) -> None:
        if self._load(business_id, str(token_hash)) is not None:
            self._collection.delete(str(token_hash))

    def mark_read(
        self, business_id: BusinessId, token_hash: IcalExportTokenHash, at: Microseconds
    ) -> None:
        def stamp(stored: IcalExportFeedDocument) -> IcalExportFeedDocument | None:
            if stored.business_id != business_id:
                return None

            return stored.model_copy(update={"last_read_at": at, "updated_at": at})

        self._collection.modify(str(token_hash), stamp)
