"""
The application wires the integrations behind their circuits (REL-04) and
a business's SMS behind its hourly volume (LOG-05): the booking systems
the busy-time sync reads go through `provider:cal_com`, Google Calendar's
mirror, eraser, busy times and consent go through
`provider:google_calendar`, Twilio's phone numbers through
`provider:twilio_numbers`, and the SMS sender staff notifications and
text-backs use counts a business's SMS.
"""

import pytest

from app.adapters.booking_systems.circuit_breaking_booking_system_adapter import (
    CircuitBreakingBookingSystemAdapter,
)
from app.adapters.calendar_sync.guarded_google_calendar_client import (
    GuardedGoogleCalendarClient,
)
from app.adapters.notifications.tenant_sms_volume_guard_adapter import (
    TenantSmsVolumeGuardAdapter,
)
from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.containers.app import AppContainer
from app.containers.phone_number_factories import build_phone_number_provisioner
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.constants.resilience import CircuitState, OutboundProvider
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberSearchQuery
from app.schemas.exceptions.application_errors import ProviderCircuitOpenError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    E164PhoneNumber,
)
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.resilience.provider_circuits import (
    guarded_circuits,
    provider_circuit,
)
from tests.e2e.workshop_container import replace_provider
from tests.resilience.test_circuit_breaker import Ticks
from tests.users.login_code_http import ScriptedProvider, json_response


def test_every_booking_system_goes_through_its_circuit() -> None:
    registry = AppContainer().facilitators.booking_system_connectors()

    for kind in BookingSystemKind:
        assert isinstance(
            registry.connector_for(kind), CircuitBreakingBookingSystemAdapter
        )


def test_the_sms_sender_counts_a_businesss_sms() -> None:
    container = AppContainer()
    twilio = ScriptedProvider(json_response(201, {"sid": "SM" + "0" * 32}))
    replace_provider(
        container.clients.twilio_messaging_client,
        TwilioMessagingClient(
            account_sid=TwilioAccountSid("AC" + "1f" * 16),
            auth_token=PlatformSecret("twilio-auth-token-secret"),
            sender=SmsSenderId("+12025550123"),
            messaging_service_sid=None,
            transport=twilio.transport(),
        ),
    )

    sender = container.adapters.resilience().sms_sender
    assert isinstance(sender, TenantSmsVolumeGuardAdapter)
    sender.send_sms(E164PhoneNumber("+393331234567"), SmsMessageText("Hi"))

    assert len(twilio.requests) == 1


def test_every_google_calendar_client_goes_through_its_circuit() -> None:
    container = AppContainer()

    clients = [
        container.facilitators.calendars.google_calendar_client(),
        container.use_cases.scheduling.google_calendar_client(),
    ]

    assert all(isinstance(client, GuardedGoogleCalendarClient) for client in clients)


def test_renting_numbers_stops_at_once_while_twilios_circuit_is_open() -> None:
    breaker = CircuitBreakerFacilitator(
        Ticks().clock(), known_circuits=guarded_circuits()
    )
    circuit = provider_circuit(OutboundProvider.TWILIO_NUMBERS)
    for _ in range(5):
        assert breaker.allows_call(circuit)
        breaker.record_failure(circuit)
    provisioner = build_phone_number_provisioner(
        assemble_app_settings(
            {
                "APP_ENV": "development",
                "PHONE_NUMBER_PROVIDER": "twilio",
                "TWILIO_ACCOUNT_SID": "AC" + "2e" * 16,
                "TWILIO_AUTH_TOKEN": "test-token-0000",
                "TWILIO_FROM_NUMBER": "+15005550006",
                "ELEVENLABS_API_KEY": "test-key-0000",
            }
        ),
        breaker,
    )

    assert breaker.state(circuit) is CircuitState.OPEN
    with pytest.raises(ProviderCircuitOpenError):
        provisioner.search_numbers(
            PhoneNumberSearchQuery(
                country_code=CountryCode("IT"), number_type=PhoneNumberType.MOBILE
            )
        )
