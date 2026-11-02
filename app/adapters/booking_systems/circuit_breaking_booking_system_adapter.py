"""A booking system connector behind its provider's circuit (REL-04)."""

from app.contracts.calendar_sync import BookingSystemConnectorContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.dto.calendar_sync.busy_reads import (
    BookingSystemBookingCreated,
    BookingSystemBookingDraft,
    BookingSystemCredentials,
    BookingSystemRead,
    BookingSystemResource,
    BusyPeriod,
)
from app.schemas.typings.calendar_sync.constrained_floats import BusyTimeFetchSeconds
from app.schemas.typings.calendar_sync.strings import BookingSystemBookingId
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.resilience.integration_outages import read_busy_source


class CircuitBreakingBookingSystemAdapter(BookingSystemConnectorContract):
    """
    Decorator of one booking system's connector (Cal.com): every call goes
    through the provider's circuit (`provider:cal_com`, shared by every
    business). Calls that timed out or could not reach the provider count
    against it; a refused key or a missing event type (one business's own
    setting) never does. While the circuit is open a call fails at once
    with BusyTimeSourceError UNREACHABLE, as the connector's own outages
    do, so the busy-time sync keeps the busy times read before and the
    queued booking writes try again later; after the circuit's wait one
    trial call goes through (half-open).
    """

    def __init__(
        self,
        inner_connector: BookingSystemConnectorContract,
        circuit_breaker: CircuitBreakerContract,
        circuit: CircuitName,
    ) -> None:
        self._inner: BookingSystemConnectorContract = inner_connector
        self._circuit_breaker: CircuitBreakerContract = circuit_breaker
        self._circuit: CircuitName = circuit
        self.kind: BookingSystemKind = inner_connector.kind

    def describe(
        self, credentials: BookingSystemCredentials, timeout: BusyTimeFetchSeconds
    ) -> BookingSystemResource:
        return read_busy_source(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.describe(credentials, timeout),
        )

    def list_busy(self, read: BookingSystemRead) -> list[BusyPeriod]:
        return read_busy_source(
            self._circuit_breaker, self._circuit, lambda: self._inner.list_busy(read)
        )

    def create_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingCreated:
        return read_busy_source(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.create_booking(credentials, draft, timeout),
        )

    def find_booking(
        self,
        credentials: BookingSystemCredentials,
        draft: BookingSystemBookingDraft,
        timeout: BusyTimeFetchSeconds,
    ) -> BookingSystemBookingId | None:
        return read_busy_source(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.find_booking(credentials, draft, timeout),
        )

    def cancel_booking(
        self,
        credentials: BookingSystemCredentials,
        booking_id: BookingSystemBookingId,
        timeout: BusyTimeFetchSeconds,
    ) -> None:
        read_busy_source(
            self._circuit_breaker,
            self._circuit,
            lambda: self._inner.cancel_booking(credentials, booking_id, timeout),
        )
