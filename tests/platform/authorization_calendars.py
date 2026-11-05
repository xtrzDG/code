"""
Two-way availability in the authorization matrix: the bodies of the
calendar changes, the operations only owners may call, and an imported
feed of business B's resource (the demo imports none).
"""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.domain.calendar_sync import (
    IcalImportFeed,
    ResourceCalendarLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_strings import CalendarFeedHost
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.calendar_sync.calendar_sync_keys import (
    resource_calendar_link_id_of,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
CALENDAR: str = f"{B}/resources/{{resource_id}}/calendar"
CALENDAR_BODIES: dict[str, JsonObject] = {
    f"PUT {CALENDAR}/google": {"calendar_id": "primary"},
    f"POST {CALENDAR}/ical-imports": {"url": "https://calendar.example/feed.ics"},
    f"PUT {CALENDAR}/booking-system": {
        "kind": "cal_com",
        "external_resource_id": "1203845",
        "api_key": "test-key-0000",
    },
}
OWNER_ONLY_CALENDAR_OPERATIONS: frozenset[str] = frozenset(
    {
        f"PUT {CALENDAR}/google",
        f"DELETE {CALENDAR}/google",
        f"POST {CALENDAR}/ical-imports",
        f"DELETE {CALENDAR}/ical-imports/{{feed_id}}",
        f"PUT {CALENDAR}/booking-system",
        f"DELETE {CALENDAR}/booking-system",
        f"POST {CALENDAR}/ical-export",
        f"DELETE {CALENDAR}/ical-export",
        f"GET {B}/integrations",
        f"GET {B}/integrations/google-calendar/calendars",
    }
)


def calendar_path_values(
    workshop: Workshop,
    storage_scope: StorageScopeContext,
    business_id: str,
    resource_id: str,
) -> dict[str, str]:
    """feed_id: a feed business B's resource imports."""

    container = workshop.container
    feed = IcalImportFeed(
        feed_id=IcalImportFeedId(),
        encrypted_url=container.adapters.secret_cipher().encrypt(
            ChannelSecret("https://calendar.example/feed.ics")
        ),
        host=CalendarFeedHost("calendar.example"),
        added_at=Microseconds(0),
    )
    with storage_scope.scoped_to_business(BusinessId(business_id)):
        container.repositories.resource_calendar_link_repo().add(
            ResourceCalendarLinkDocument(
                id=resource_calendar_link_id_of(ResourceId(resource_id)),
                business_id=BusinessId(business_id),
                resource_id=ResourceId(resource_id),
                ical_imports=[feed],
            )
        )

    return {"feed_id": str(feed.feed_id)}
