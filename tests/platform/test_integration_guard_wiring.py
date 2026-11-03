"""
The application wires the integrations behind their circuits (REL-04) and
a business's SMS behind its hourly volume (LOG-05): the booking systems
the busy-time sync reads go through `provider:cal_com`, and the SMS sender
staff notifications and text-backs use counts a business's SMS.
"""

from app.adapters.booking_systems.circuit_breaking_booking_system_adapter import (
    CircuitBreakingBookingSystemAdapter,
)
from app.adapters.notifications.tenant_sms_volume_guard_adapter import (
    TenantSmsVolumeGuardAdapter,
)
from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.containers.app import AppContainer
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from tests.e2e.workshop_container import replace_provider
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
