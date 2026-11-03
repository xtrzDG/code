"""
The world of the abuse alerts' tests (ABUSE-04, VOICE-09): the platform
operations world with a booking store and the booking surge observer.
"""

from collections.abc import Sequence

from base_typed_id import BasePrefixedTypedId
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.monitoring.booking_surge_observer_facilitator import (
    BookingSurgeObserverFacilitator,
)
from app.repositories.booking_repositories import BookingRepository
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.domain.bookings import BookingDocument
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
from tests.platform_ops.ops_documents import SECOND
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


def quality_change(field: str, **value: str) -> JsonObject:
    """One change of a WhatsApp webhook entry, as Meta sends it."""

    return {"field": field, "value": dict(value)}
