"""Staff e-mail, SMS and WhatsApp notifications as their providers get them."""

import pytest

from app.clients.twilio.twilio_messaging_client import TwilioMessagingClient
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
    mask_address,
)
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.exceptions.application_errors import (
    DeliveryNotConfiguredError,
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.messaging.constrained_strings import (
    SmsSenderId,
    TwilioAccountSid,
)
from app.schemas.typings.messaging.strings import SmsMessageText
from app.schemas.typings.platform.strings import PlatformSecret
from tests.channels.channels_settings import build_settings
from tests.channels.testbed import ChannelsTestbed
from tests.users.login_code_fakes import FakeMailer, FakeSms
from tests.users.login_code_http import ScriptedProvider, json_response

BRIEF = MessageText(
    "New booking · Salobie Bia\n"
    "Tomorrow 19:00 · 2 guests\n"
    "Open: https://cabinet.example.com/n/token_1"
)


def contact(channel: ManagerContactChannel, address: str) -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Anna"),
        channel=channel,
        address=ManagerContactAddress(address),
        language=LanguageTag("en"),
    )


def sender(
    testbed: ChannelsTestbed,
    mailer: FakeMailer | None = None,
    sms: FakeSms | None = None,
) -> StaffNotificationSenderFacilitator:
    return StaffNotificationSenderFacilitator(
        testbed.telegram_client,
        testbed.whatsapp_adapter,
        testbed.settings,
        email_client=mailer,
        sms_client=sms,
    )


def test_an_email_has_the_title_as_subject_and_the_link_as_a_button() -> None:
    mailer = FakeMailer()

    sender(ChannelsTestbed(), mailer=mailer).send(
        contact(ManagerContactChannel.EMAIL, "anna@example.com"), BRIEF, None
    )

    [email] = mailer.sent
    assert str(email.recipient) == "anna@example.com"
    assert str(email.subject) == "New booking · Salobie Bia"
    assert str(email.text_body).startswith(str(BRIEF))
    assert email.html_body is not None
    assert 'href="https://cabinet.example.com/n/token_1"' in str(email.html_body)
    assert ">Open</a>" in str(email.html_body)


def test_an_sms_is_the_brief_text_itself() -> None:
    sms = FakeSms()

    sender(ChannelsTestbed(), sms=sms).send(
        contact(ManagerContactChannel.SMS, "+995555000222"), BRIEF, None
    )

    assert sms.sent == [(E164PhoneNumber("+995555000222"), SmsMessageText(str(BRIEF)))]


def test_a_whatsapp_template_parameter_is_one_line() -> None:
    testbed = ChannelsTestbed()
    testbed.meta_transport.respond(
        "POST", r"/messages$", {"messages": [{"id": "wamid.1"}]}
    )

    testbed.staff_notifier.notify(
        StaffNotification(
            business_id=BusinessId(),
            contact=contact(ManagerContactChannel.WHATSAPP, "+995599123456"),
            text=BRIEF,
        )
    )
    testbed.run_worker()

    [request] = testbed.meta_transport.requests
    [parameter] = request.json()["template"]["components"][0]["parameters"]
    assert parameter["text"] == (
        "New booking · Salobie Bia · Tomorrow 19:00 · 2 guests · "
        "Open: https://cabinet.example.com/n/token_1"
    )


def test_without_a_provider_in_production_nothing_is_sent() -> None:
    production = ChannelsTestbed(build_settings(APP_ENV="production"))

    with pytest.raises(DeliveryNotConfiguredError, match="No sms provider"):
        sender(production).send(
            contact(ManagerContactChannel.SMS, "+995555000222"), BRIEF, None
        )
    assert mask_address("ab") == "***"


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (400, ProviderRejectedMessageError),
        (401, DeliveryNotConfiguredError),
        (429, ProviderRateLimitedError),
        (503, ExternalServiceError),
    ],
)
def test_twilio_refusals_say_whether_to_retry(
    status: int, kind: type[ExternalServiceError]
) -> None:
    client = TwilioMessagingClient(
        account_sid=TwilioAccountSid("AC" + "1f" * 16),
        auth_token=PlatformSecret("twilio-auth-token-secret"),
        sender=SmsSenderId("+12025550123"),
        messaging_service_sid=None,
        transport=ScriptedProvider(json_response(status, {"code": 21211})).transport(),
    )

    with pytest.raises(ExternalServiceError) as raised:
        client.send_sms(E164PhoneNumber("+995555000222"), SmsMessageText("Hi"))

    assert type(raised.value) is kind
