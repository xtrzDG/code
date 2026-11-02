"""
The abuse alerts (ABUSE-04, VOICE-09): a business past 40 new bookings or
15 cancellations in an hour, and Meta's warnings about a WhatsApp number
or template, each counted where the event happens and read by the
platform alerts job.
"""

from collections.abc import Sequence

import pytest
from base_typed_id import BasePrefixedTypedId
from typed_time_provider import Microseconds

from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.channels.whatsapp_quality_signals import report_quality_warnings
from app.adapters.events.in_memory_live_event_bus_adapter import (
    InMemoryLiveEventBusAdapter,
)
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.events.event_publisher_facilitator import (
    EventPublisherFacilitator,
)
from app.facilitators.monitoring.booking_surge_observer_facilitator import (
    BOOKING_SURGE_PER_HOUR,
    CANCELLATION_SURGE_PER_HOUR,
    BookingSurgeObserverFacilitator,
)
from app.repositories.booking_repositories import BookingRepository
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload
from app.schemas.dto.platform_alerts import AlertObservation
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.utilities.channels.json_values import JsonObject
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.testbed import ChannelsTestbed
from tests.platform_ops.ops_documents import HOUR, MINUTE, SECOND
from tests.platform_ops.ops_world import OpsWorld


class BookingWorld:
    def __init__(self) -> None:
        self.ops = OpsWorld()
        self.bookings = BookingRepository(
            InMemoryDocumentCollectionAdapter(BookingDocument)
        )
        self.observer = BookingSurgeObserverFacilitator(
            booking_repo=self.bookings,
            buckets=self.ops.buckets,
            signal_counter=self.ops.signals,
            storage_scope=StorageScopeContext(),
            wall_clock=self.ops.clock.wall_clock,
        )

    def announce(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId] = (),
        times: int = 1,
    ) -> None:
        for _ in range(times):
            self.observer.notice(business_id, event, ids)

    def booking(
        self, business_id: BusinessId, status: BookingStatus, age_seconds: int = 0
    ) -> BookingId:
        written = Microseconds(self.ops.clock.now - age_seconds * SECOND)
        booking = BookingDocument(
            business_id=business_id,
            resource_id=ResourceId(),
            contact_id=ContactId(),
            starts_at=BookingStartsAtUnixSeconds(1_900_000_000),
            ends_at=BookingEndsAtUnixSeconds(1_900_003_600),
            party_size=PartySize(2),
            status=status,
            source_channel=ChannelKind.WEB_CHAT,
            created_at=written,
            updated_at=written,
        )
        self.bookings.save(booking)
        return booking.id

    def observe(self, code: PlatformAlertCode) -> AlertObservation:
        [observation] = self.ops.checks().run(
            {code: PLATFORM_ALERT_RULES[code]}, self.ops.clock.wall_clock.now_unix()
        )
        return observation

    def signals(self, signal: PlatformSignal) -> int:
        tally = self.ops.signals.read(signal, self.ops.clock.wall_clock.now_unix())
        return int(tally.current) + int(tally.previous)


@pytest.fixture
def world() -> BookingWorld:
    return BookingWorld()


def test_forty_new_bookings_an_hour_stay_quiet(world: BookingWorld) -> None:
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=40)

    assert BOOKING_SURGE_PER_HOUR == 40
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0
    assert not world.observe(PlatformAlertCode.BOOKING_SPIKE).is_firing


def test_the_41st_new_booking_fires_the_alert_once(
    world: BookingWorld, caplog: pytest.LogCaptureFixture
) -> None:
    business_id = BusinessId()

    world.announce(business_id, LiveEventKind.BOOKING_CREATED, times=60)

    assert world.signals(PlatformSignal.BOOKING_SURGE) == 1
    observation = world.observe(PlatformAlertCode.BOOKING_SPIKE)
    assert observation.is_firing
    assert "past 40 new bookings" in str(observation.detail)
    # The log names the business, never a customer.
    assert str(business_id) in caplog.text


def test_new_bookings_count_per_business_and_hour(world: BookingWorld) -> None:
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=30)
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=30)
    world.ops.clock.advance(HOUR)
    world.announce(BusinessId(), LiveEventKind.BOOKING_CREATED, times=30)

    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0


def test_the_16th_cancellation_an_hour_fires_the_alert(world: BookingWorld) -> None:
    business_id = BusinessId()
    cancelled = [world.booking(business_id, BookingStatus.CANCELLED) for _ in range(16)]

    for booking_id in cancelled[:15]:
        world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (booking_id,))
    assert CANCELLATION_SURGE_PER_HOUR == 15
    assert not world.observe(PlatformAlertCode.CANCELLATION_SPIKE).is_firing

    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (cancelled[15],))

    assert world.signals(PlatformSignal.CANCELLATION_SURGE) == 1
    assert world.observe(PlatformAlertCode.CANCELLATION_SPIKE).is_firing


@pytest.mark.parametrize(
    ("status", "age_seconds"),
    [
        # Moved or confirmed: a change, not a cancellation.
        (BookingStatus.CONFIRMED, 0),
        # Cancelled long ago: a later change of it is no new cancellation.
        (BookingStatus.CANCELLED, 5 * 60),
    ],
)
def test_other_booking_changes_are_no_cancellations(
    world: BookingWorld, status: BookingStatus, age_seconds: int
) -> None:
    business_id = BusinessId()
    booking_id = world.booking(business_id, status, age_seconds)

    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (booking_id,), 30)

    assert world.signals(PlatformSignal.CANCELLATION_SURGE) == 0


def test_a_change_without_a_booking_counts_nothing(world: BookingWorld) -> None:
    business_id = BusinessId()

    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (BookingId(),), 30)
    world.announce(business_id, LiveEventKind.BOOKING_CHANGED, (), 30)
    world.announce(business_id, LiveEventKind.LEAD_CREATED, times=60)

    assert world.signals(PlatformSignal.CANCELLATION_SURGE) == 0
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0


def test_owners_test_bookings_never_count(world: BookingWorld) -> None:
    publisher = EventPublisherFacilitator(
        InMemoryLiveEventBusAdapter(),
        world.ops.clock.wall_clock,
        observers=[world.observer],
    )
    business_id = BusinessId()

    for _ in range(60):
        publisher.publish(business_id, LiveEventKind.BOOKING_CREATED, is_sandbox=True)
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 0

    for _ in range(41):
        publisher.publish(business_id, LiveEventKind.BOOKING_CREATED)
    assert world.signals(PlatformSignal.BOOKING_SURGE) == 1


def quality_change(field: str, **value: str) -> JsonObject:
    return {"field": field, "value": dict(value)}


@pytest.mark.parametrize(
    "change",
    [
        quality_change("phone_number_quality_update", event="FLAGGED"),
        quality_change("phone_number_quality_update", event="DOWNGRADE"),
        quality_change(
            "message_template_quality_update",
            new_quality_score="RED",
            message_template_name="reminder",
            message_template_language="it",
        ),
        quality_change(
            "message_template_status_update",
            event="PAUSED",
            message_template_name="reminder",
        ),
        quality_change(
            "template_category_update",
            new_category="MARKETING",
            message_template_name="text_back",
        ),
    ],
)
def test_meta_warnings_fire_the_whatsapp_quality_alert(
    world: BookingWorld, change: JsonObject, caplog: pytest.LogCaptureFixture
) -> None:
    report_quality_warnings(change, world.ops.signals)

    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 1
    assert world.observe(PlatformAlertCode.WHATSAPP_QUALITY).is_firing
    assert "WhatsApp quality warning" in caplog.text


@pytest.mark.parametrize(
    "change",
    [
        quality_change("phone_number_quality_update", event="UPGRADE"),
        quality_change("message_template_quality_update", new_quality_score="GREEN"),
        quality_change("message_template_status_update", event="APPROVED"),
        quality_change("template_category_update", new_category="UTILITY"),
        quality_change("account_update", event="VERIFIED_ACCOUNT"),
    ],
)
def test_good_news_from_meta_stays_quiet(
    world: BookingWorld, change: JsonObject
) -> None:
    report_quality_warnings(change, world.ops.signals)
    world.ops.clock.advance(MINUTE)

    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 0
    assert not world.observe(PlatformAlertCode.WHATSAPP_QUALITY).is_firing


def test_the_whatsapp_webhook_counts_meta_s_warnings(world: BookingWorld) -> None:
    testbed = ChannelsTestbed()
    adapter = WhatsAppChannelAdapter(
        testbed.meta_client,
        testbed.phone_number_parser,
        testbed.settings,
        signal_counter=world.ops.signals,
    )
    body = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "102290129340398",
                "changes": [
                    quality_change("phone_number_quality_update", event="FLAGGED"),
                    quality_change(
                        "message_template_quality_update",
                        new_quality_score="YELLOW",
                        message_template_name="text_back",
                    ),
                ],
            }
        ],
    }

    messages = adapter.parse_webhook(ChannelWebhookPayload(body=to_json_bytes(body)))

    assert messages == []
    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 2
