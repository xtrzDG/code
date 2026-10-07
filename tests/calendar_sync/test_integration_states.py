"""
How Settings → Integrations sums the resources' sources: an integration's
own read (Google's account check) counts, the Google calendar comes first
among a resource's sources, a resource with nothing linked and nothing
shared is left out, and a summary counts sources and problems.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.calendar_sync import (
    BookingSystemKind,
    CalendarSyncProblem,
    IntegrationKind,
    IntegrationState,
)
from app.schemas.domain.calendar_sync import (
    BookingSystemLink,
    BusySourceStatus,
    IcalImportFeed,
    ResourceCalendarLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
    CalendarFeedHost,
    IcalExportTokenHash,
)
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.use_cases.calendar_sync.integration_states import (
    integration_view,
    resource_summaries,
    source_statuses,
)
from app.utilities.calendar_sync.calendar_sync_keys import (
    resource_calendar_link_id_of,
)

BUSINESS: BusinessId = BusinessId()
SEALED: EncryptedChannelSecret = EncryptedChannelSecret("sealed-test-0000")


def synced(at: int) -> BusySourceStatus:
    return BusySourceStatus(
        last_attempt_at=Microseconds(at), last_synced_at=Microseconds(at)
    )


def failed(at: int) -> BusySourceStatus:
    return BusySourceStatus(
        last_attempt_at=Microseconds(at), problem=CalendarSyncProblem.TIMEOUT
    )


def link(
    *,
    google: BusySourceStatus | None = None,
    feeds: tuple[BusySourceStatus, ...] = (),
    booking: BusySourceStatus | None = None,
    shared: bool = False,
) -> ResourceCalendarLinkDocument:
    resource: ResourceId = ResourceId()
    return ResourceCalendarLinkDocument(
        id=resource_calendar_link_id_of(resource),
        business_id=BUSINESS,
        resource_id=resource,
        google_status=google,
        ical_imports=[
            IcalImportFeed(
                feed_id=IcalImportFeedId(),
                encrypted_url=SEALED,
                host=CalendarFeedHost("www.airbnb.com"),
                added_at=Microseconds(1),
                status=status,
            )
            for status in feeds
        ],
        booking_system=None
        if booking is None
        else BookingSystemLink(
            kind=BookingSystemKind.CAL_COM,
            external_resource_id=BookingSystemResourceId("1203845"),
            encrypted_api_key=SEALED,
            added_at=Microseconds(1),
            status=booking,
        ),
        ical_export_token_hash=IcalExportTokenHash("0" * 64) if shared else None,
    )


def test_an_integrations_own_read_turns_it_on_and_counts_as_its_last_read() -> None:
    off = integration_view(IntegrationKind.GOOGLE_CALENDAR, [])
    assert off.state == IntegrationState.OFF
    assert off.last_synced_at is None

    own = integration_view(
        IntegrationKind.GOOGLE_CALENDAR, [], extra_synced_at=Microseconds(50)
    )
    assert own.state == IntegrationState.ON
    assert own.last_synced_at == 50

    later = integration_view(
        IntegrationKind.GOOGLE_CALENDAR,
        [[synced(70)]],
        extra_synced_at=Microseconds(50),
    )
    assert later.last_synced_at == 70
    assert later.resource_count == 1

    broken = integration_view(
        IntegrationKind.GOOGLE_CALENDAR, [[synced(70)]], extra_attention=True
    )
    assert broken.state == IntegrationState.ATTENTION
    assert broken.attention_count == 0


def test_google_comes_first_then_feeds_then_the_booking_system() -> None:
    google, feed, booking = synced(1), synced(2), synced(3)
    statuses = source_statuses(link(google=google, feeds=(feed,), booking=booking))
    assert statuses == [google, feed, booking]
    assert source_statuses(link()) == []


def test_summaries_leave_out_resources_with_nothing_and_count_problems() -> None:
    quiet = link()
    shared_only = link(shared=True)
    mixed = link(google=synced(10), feeds=(failed(20), synced(30)))

    summaries = resource_summaries([quiet, shared_only, mixed])

    assert [summary.resource_id for summary in summaries] == [
        shared_only.resource_id,
        mixed.resource_id,
    ]
    shared_summary, mixed_summary = summaries
    assert shared_summary.is_export_on is True
    assert shared_summary.source_count == 0
    assert shared_summary.last_synced_at is None
    assert mixed_summary.source_count == 3
    assert mixed_summary.problem_count == 1
    assert mixed_summary.last_synced_at == 30
    assert mixed_summary.is_export_on is False
