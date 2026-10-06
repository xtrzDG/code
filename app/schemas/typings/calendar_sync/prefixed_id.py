"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class CalendarBusyTimesId(BasePrefixedTypedId):
    """
    Identifier of the busy times one calendar source (Google, an iCal feed,
    a booking system) holds for one resource.

    Derived (UUID v5) from the resource and the source, so each pair has
    one document.
    """

    prefix = "busy_times"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class IcalExportFeedId(BasePrefixedTypedId):
    """
    Identifier of one iCal export address of a resource (made again, the old
    address stops working and the new one has a new id).

    Example:
        feed_id = IcalExportFeedId()
    """

    prefix = "ical_export"


class ResourceCalendarLinkId(BasePrefixedTypedId):
    """
    Identifier of the calendar settings of one resource: the iCal feed it
    imports, its export address, the booking system it follows, and how
    each of them synced last.

    Derived (UUID v5) from the resource, so a resource has one document.
    """

    prefix = "resource_calendar"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


# Keep abc order for all non example types, if possible.
