"""
Identities of two-way availability: the calendar settings of a resource,
the busy times of each of its sources, and the export address's token.
"""

import hashlib
import secrets
from uuid import UUID, uuid5

from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.calendar_sync.constrained_strings import IcalExportTokenHash
from app.schemas.typings.calendar_sync.prefixed_id import (
    CalendarBusyTimesId,
    IcalImportFeedId,
    ResourceCalendarLinkId,
)
from app.schemas.typings.calendar_sync.strings import IcalExportToken

# Fixed namespaces of derived ids (never change them: stored ids depend on them).
RESOURCE_CALENDAR_NAMESPACE: UUID = UUID("0b6f3c52-6a1e-4f0e-9d0e-5a7c41d2e8b3")
BUSY_TIMES_NAMESPACE: UUID = UUID("7d2a9e14-3c5b-4b8f-a1e6-2f9c0d4b6a57")
# 32 random bytes: an export address cannot be guessed.
EXPORT_TOKEN_BYTES: int = 32


def resource_calendar_link_id_of(resource_id: ResourceId) -> ResourceCalendarLinkId:
    """One calendar settings document per resource."""

    return ResourceCalendarLinkId(uuid5(RESOURCE_CALENDAR_NAMESPACE, str(resource_id)))


def busy_times_id_of(
    resource_id: ResourceId,
    source: BusyTimeSource,
    feed_id: IcalImportFeedId | None = None,
) -> CalendarBusyTimesId:
    """One busy-times document per resource and source (per feed for iCal)."""

    name: str = f"{resource_id}:{source.value}:{'' if feed_id is None else feed_id}"
    return CalendarBusyTimesId(uuid5(BUSY_TIMES_NAMESPACE, name))


def generate_export_token() -> IcalExportToken:
    """An unguessable token for a new export address (URL-safe)."""

    return IcalExportToken(secrets.token_urlsafe(EXPORT_TOKEN_BYTES))


def hash_export_token(token: IcalExportToken) -> IcalExportTokenHash:
    return IcalExportTokenHash(hashlib.sha256(str(token).encode("utf-8")).hexdigest())
