"""
A key rotation seals resources' calendar secrets again: imported feeds'
addresses and booking systems' keys move to the current key, those sealed
with it already are left alone, a feed replaced during the run keeps its
new address, and a secret no key opens is counted, not lost.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.adapters.security.secret_cipher_adapter import SecretCipherAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.calendar_sync_repositories import ResourceCalendarLinkRepository
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.domain.calendar_sync import (
    BookingSystemLink,
    IcalImportFeed,
    ResourceCalendarLinkDocument,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
    CalendarFeedHost,
)
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.admin.security.secret_resealer import RotationTally, SecretResealer
from app.utilities.calendar_sync.calendar_sync_keys import (
    resource_calendar_link_id_of,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.security.test_secret_resealer import (
    NEW_KEY,
    OLD,
    OLD_KEY,
    RecordingTelegram,
    calendar_repo,
    channel_repo,
)

BUSINESS: BusinessId = BusinessId()
RESOURCE: ResourceId = ResourceId()
FIRST_FEED: str = "https://www.airbnb.com/calendar/ical/1.ics?s=test-feed-0000"
SECOND_FEED: str = "https://admin.booking.com/ical/2.ics?t=test-feed-0001"
API_KEY: str = "cal_test_key_0000"
FOREIGN_KEY: str = "calendar-foreign-encryption-key-00000000"  # gitleaks:allow
RING_SETTINGS = assemble_app_settings({"ENCRYPTION_KEYS": f"{NEW_KEY},{OLD_KEY}"})
RING: SecretCipherAdapter = SecretCipherAdapter(RING_SETTINGS)
NEW_ONLY: SecretCipherAdapter = SecretCipherAdapter(
    assemble_app_settings({"ENCRYPTION_KEYS": NEW_KEY})
)
FOREIGN: SecretCipherAdapter = SecretCipherAdapter(
    assemble_app_settings({"ENCRYPTION_KEYS": FOREIGN_KEY})
)


def feed(url: str, sealed_by: SecretCipherAdapter) -> IcalImportFeed:
    return IcalImportFeed(
        feed_id=IcalImportFeedId(),
        encrypted_url=sealed_by.encrypt(ChannelSecret(url)),
        host=CalendarFeedHost("www.airbnb.com"),
        added_at=Microseconds(1),
    )


def link(
    *feeds: IcalImportFeed, key_sealed_by: SecretCipherAdapter = OLD
) -> ResourceCalendarLinkDocument:
    return ResourceCalendarLinkDocument(
        id=resource_calendar_link_id_of(RESOURCE),
        business_id=BUSINESS,
        resource_id=RESOURCE,
        ical_imports=list(feeds),
        booking_system=BookingSystemLink(
            kind=BookingSystemKind.CAL_COM,
            external_resource_id=BookingSystemResourceId("1203845"),
            encrypted_api_key=key_sealed_by.encrypt(ChannelSecret(API_KEY)),
            added_at=Microseconds(1),
        ),
        created_at=Microseconds(1),
        updated_at=Microseconds(1),
    )


class RacingLinkRepository(ResourceCalendarLinkRepository):
    """The owner replaces the first feed just before the run writes."""

    def update(
        self,
        business_id: BusinessId,
        resource_id: ResourceId,
        change: Callable[
            [ResourceCalendarLinkDocument], ResourceCalendarLinkDocument | None
        ],
    ) -> ResourceCalendarLinkDocument | None:
        def replace_first(
            stored: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument:
            stored.ical_imports[0].encrypted_url = RING.encrypt(
                ChannelSecret(SECOND_FEED)
            )
            return stored

        super().update(business_id, resource_id, replace_first)
        return super().update(business_id, resource_id, change)


def link_repo(
    kind: type[ResourceCalendarLinkRepository] = ResourceCalendarLinkRepository,
) -> ResourceCalendarLinkRepository:
    return kind(
        InMemoryDocumentCollectionAdapter[ResourceCalendarLinkDocument](
            ResourceCalendarLinkDocument
        )
    )


def run(links: ResourceCalendarLinkRepository) -> RotationTally:
    resealer = SecretResealer(
        channel_repo=channel_repo(),
        calendar_connection_repo=calendar_repo(),
        secret_cipher=RING,
        secret_rotation=RING,
        telegram_client=RecordingTelegram(),
        app_settings=RING_SETTINGS,
        calendar_link_repo=links,
    )
    tally = RotationTally()
    resealer.reseal_business(BUSINESS, tally)
    return tally


def stored_link(links: ResourceCalendarLinkRepository) -> ResourceCalendarLinkDocument:
    stored = links.get(BUSINESS, RESOURCE)
    assert stored is not None
    return stored


def test_feed_addresses_and_keys_move_to_the_current_key() -> None:
    links = link_repo()
    links.add(link(feed(FIRST_FEED, OLD), feed(SECOND_FEED, RING)))

    tally = run(links)

    stored = stored_link(links)
    assert stored.booking_system is not None
    assert [str(NEW_ONLY.decrypt(f.encrypted_url)) for f in stored.ical_imports] == [
        FIRST_FEED,
        SECOND_FEED,
    ]
    assert str(NEW_ONLY.decrypt(stored.booking_system.encrypted_api_key)) == API_KEY
    assert (tally.total, tally.rotated, tally.current) == (3, 2, 1)


def test_a_feed_replaced_during_the_run_keeps_its_new_address() -> None:
    links = link_repo(RacingLinkRepository)
    links.add(link(feed(FIRST_FEED, OLD)))

    run(links)

    stored = stored_link(links)
    assert stored.booking_system is not None
    assert str(NEW_ONLY.decrypt(stored.ical_imports[0].encrypted_url)) == SECOND_FEED
    assert str(NEW_ONLY.decrypt(stored.booking_system.encrypted_api_key)) == API_KEY


def test_secrets_no_key_opens_are_counted_and_kept() -> None:
    links = link_repo()
    unreadable = feed(FIRST_FEED, FOREIGN)
    links.add(link(unreadable, key_sealed_by=RING))

    tally = run(links)

    stored = stored_link(links)
    assert stored.ical_imports[0].encrypted_url == unreadable.encrypted_url
    assert (tally.unreadable, tally.current) == (1, 1)
