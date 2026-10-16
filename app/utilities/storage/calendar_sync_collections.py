"""
The catalog entries of the calendars: Google Calendar's connection, OAuth
state and event per booking (0002), and two-way availability (1160). Part
of DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).

- resource_calendar_links: one document per resource, read by id; the
  sync job finds the ones due across businesses (`next_sync_at`);
- calendar_busy_times: one document per resource and source, read by id
  and, for a placement, every one of the business (by `business_id`);
- ical_export_feeds: one document per export address, read by the hash
  of its token (the document's key) when a calendar fetches the feed.
"""

from collections.abc import Mapping

from app.schemas.domain.calendar import (
    CalendarAuthorizationStateDocument,
    CalendarConnectionDocument,
    CalendarEventLinkDocument,
)
from app.schemas.domain.calendar_sync import (
    CalendarBusyTimesDocument,
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field

RESOURCE_CALENDAR_LINKS: DocumentCollectionName = DocumentCollectionName(
    "resource_calendar_links"
)
CALENDAR_BUSY_TIMES: DocumentCollectionName = DocumentCollectionName(
    "calendar_busy_times"
)
ICAL_EXPORT_FEEDS: DocumentCollectionName = DocumentCollectionName("ical_export_feeds")

CALENDAR_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("calendar_connections"), CalendarConnectionDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("calendar_authorization_states"),
        CalendarAuthorizationStateDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("calendar_event_links"), CalendarEventLinkDocument
    ),
    DocumentCollectionDefinition(RESOURCE_CALENDAR_LINKS, ResourceCalendarLinkDocument),
    DocumentCollectionDefinition(CALENDAR_BUSY_TIMES, CalendarBusyTimesDocument),
    DocumentCollectionDefinition(ICAL_EXPORT_FEEDS, IcalExportFeedDocument),
)

CALENDAR_SYNC_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    RESOURCE_CALENDAR_LINKS: (integer_field("next_sync_at"),),
}
