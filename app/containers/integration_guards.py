"""
The businesses' integrations behind their circuits (REL-04): Google
Calendar, the booking systems (Cal.com) and Twilio's phone numbers, each
with its own `provider:*` circuit of the process's one circuit breaker.
"""

from app.adapters.booking_systems.circuit_breaking_booking_system_adapter import (
    CircuitBreakingBookingSystemAdapter,
)
from app.adapters.calendar_sync.guarded_google_calendar_client import (
    GuardedGoogleCalendarClient,
)
from app.adapters.telephony.guarded_twilio_phone_numbers_client import (
    GuardedTwilioPhoneNumbersClient,
)
from app.contracts.calendar_sync import BookingSystemConnectorContract
from app.contracts.operations import GoogleCalendarClientContract
from app.contracts.resilience import CircuitBreakerContract
from app.contracts.telephony_clients import TwilioPhoneNumbersClientContract
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.constants.resilience import OutboundProvider
from app.utilities.resilience.provider_circuits import provider_circuit

BOOKING_SYSTEM_PROVIDERS: dict[BookingSystemKind, OutboundProvider] = {
    BookingSystemKind.CAL_COM: OutboundProvider.CAL_COM,
}


def guard_google_calendar_client(
    inner_client: GoogleCalendarClientContract,
    circuit_breaker: CircuitBreakerContract,
) -> GoogleCalendarClientContract:
    """Google Calendar behind `provider:google_calendar`."""

    return GuardedGoogleCalendarClient(
        inner_client,
        circuit_breaker,
        provider_circuit(OutboundProvider.GOOGLE_CALENDAR),
    )


def guard_booking_system(
    connector: BookingSystemConnectorContract,
    circuit_breaker: CircuitBreakerContract,
) -> BookingSystemConnectorContract:
    """A booking system's connector behind its provider's circuit."""

    return CircuitBreakingBookingSystemAdapter(
        connector,
        circuit_breaker,
        provider_circuit(BOOKING_SYSTEM_PROVIDERS[connector.kind]),
    )


def guard_twilio_phone_numbers(
    inner_client: TwilioPhoneNumbersClientContract,
    circuit_breaker: CircuitBreakerContract,
) -> TwilioPhoneNumbersClientContract:
    """Twilio's phone numbers behind `provider:twilio_numbers`."""

    return GuardedTwilioPhoneNumbersClient(
        inner_client,
        circuit_breaker,
        provider_circuit(OutboundProvider.TWILIO_NUMBERS),
    )
