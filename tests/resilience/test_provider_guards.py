"""
Every outbound provider sits behind its circuit: while the circuit is open a
send fails at once and nothing reaches the provider; reading webhooks and
notifications never waits on a circuit.
"""

from collections.abc import Callable, Sequence

import pytest

from app.adapters.channels.circuit_breaking_channel_adapter import (
    CircuitBreakingChannelAdapter,
)
from app.adapters.channels.circuit_breaking_whatsapp_template_adapter import (
    CircuitBreakingWhatsAppTemplateAdapter,
)
from app.adapters.notifications.circuit_breaking_telegram_bot_adapter import (
    CircuitBreakingTelegramBotAdapter,
)
from app.adapters.payments.circuit_breaking_payment_gateway_adapter import (
    CircuitBreakingPaymentGatewayAdapter,
)
from app.containers.adapters.provider_guards import (
    guard_email_sender,
    guard_sms_sender,
)
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.payments import PaymentProvider
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelWebhookPayload,
)
from app.schemas.dto.messaging import EmailAttachment
from app.schemas.dto.payment_retries import PaymentRetryRequest, PaymentRetryResult
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentWebhookDelivery,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import ProviderCircuitOpenError
from app.schemas.typings.billing.strings import (
    PaymentProviderReference,
    PaymentWebhookBody,
)
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    MetaObjectId,
    TelegramBotUserId,
    TelegramWebhookSecret,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import (
    ChannelSecret,
    OutboundMessagePart,
    ProviderMessageId,
    TelegramCallbackQueryId,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.strings import (
    EmailBodyText,
    EmailSubject,
    SmsMessageText,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.billing.test_flitt_payment_gateway import build_checkout_request
from tests.channels.channels_settings import PLATFORM_BOT_TOKEN
from tests.channels.testbed import ChannelsTestbed
from tests.resilience.test_circuit_breaker import Ticks

TARGET = ChannelDeliveryTarget(
    channel=ChannelKind.WHATSAPP,
    account_id=None,
    channel_user_id=ChannelUserId("995599000001"),
)


def open_breaker(circuit: CircuitName) -> CircuitBreakerFacilitator:
    breaker = CircuitBreakerFacilitator(Ticks().clock())
    for _ in range(5):
        breaker.record_failure(circuit)
    return breaker


class RecordingSenders:
    """E-mail, SMS and payments that record what reached them."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_email(
        self,
        recipient: EmailAddress,
        subject: EmailSubject,
        text_body: EmailBodyText,
        html_body: EmailBodyText | None,
        attachments: Sequence[EmailAttachment] = (),
    ) -> None:
        del recipient, subject, text_body, html_body, attachments
        self.calls.append("send_email")

    def send_sms(self, recipient: E164PhoneNumber, text: SmsMessageText) -> None:
        del recipient, text
        self.calls.append("send_sms")

    def create_checkout(
        self, request: PaymentCheckoutRequest
    ) -> PaymentCheckoutSession:
        del request
        raise AssertionError("A checkout reached the provider.")

    def read_notification(
        self, delivery: PaymentWebhookDelivery
    ) -> VerifiedPaymentEvent:
        del delivery
        self.calls.append("read_notification")
        raise LookupError("not a real notification")

    def stop_recurring(
        self, provider: PaymentProvider, provider_reference: PaymentProviderReference
    ) -> None:
        del provider, provider_reference
        self.calls.append("stop_recurring")

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        del request
        raise AssertionError("A retried charge reached the provider.")


def test_an_open_meta_circuit_sends_nothing_but_webhooks_are_still_read() -> None:
    testbed = ChannelsTestbed()
    meta = provider_circuit(OutboundProvider.META)
    breaker = open_breaker(meta)
    whatsapp = CircuitBreakingChannelAdapter(testbed.whatsapp_adapter, breaker, meta)
    templates = CircuitBreakingWhatsAppTemplateAdapter(
        testbed.whatsapp_adapter, breaker, meta
    )

    with pytest.raises(ProviderCircuitOpenError) as refused:
        whatsapp.send(TARGET, MessageText("Your table is booked."))
    with pytest.raises(ProviderCircuitOpenError):
        whatsapp.signal_typing(TARGET, ProviderMessageId("wamid.in"))
    with pytest.raises(ProviderCircuitOpenError):
        templates.send_template(
            MetaObjectId("106540352242922"),
            ChannelUserId("995599000001"),
            WhatsAppTemplateName("booking_reminder"),
            WhatsAppTemplateLanguageCode("ka"),
            [MessageText("Salobie Bia")],
        )

    assert int(refused.value.retry_after_seconds or 0) == 30
    assert testbed.meta_transport.requests == []
    # Splitting, signatures, payloads and taps need no provider.
    assert whatsapp.split(MessageText("Hello.")) == [MessageText("Hello.")]
    payload = ChannelWebhookPayload(body=b'{"entry": []}')
    assert whatsapp.parse_webhook(payload) == []
    whatsapp.acknowledge_taps(payload, None)
    with pytest.raises(Exception, match="signature"):
        whatsapp.verify_signature(payload, ChannelSecret("app-secret"))


def test_an_open_platform_bot_circuit_refuses_every_bot_call() -> None:
    testbed = ChannelsTestbed()
    circuit = provider_circuit(OutboundProvider.PLATFORM_BOT)
    bot = CircuitBreakingTelegramBotAdapter(
        testbed.telegram_client, open_breaker(circuit), circuit
    )
    token = ChannelSecret(PLATFORM_BOT_TOKEN)
    chat = ChannelUserId("100200300")
    calls: list[Callable[[], object]] = [
        lambda: bot.get_me(token),
        lambda: bot.get_profile_photo_file_id(token, TelegramBotUserId("700000001")),
        lambda: bot.set_webhook(
            token,
            ChannelWebhookUrl("https://api.assistant.example/v1/telegram"),
            TelegramWebhookSecret("secret-0000"),
        ),
        lambda: bot.delete_webhook(token),
        lambda: bot.send_message(token, chat, OutboundMessagePart("Alert.")),
        lambda: bot.answer_callback_query(token, TelegramCallbackQueryId("42")),
        lambda: bot.edit_message_text(
            token, ProviderMessageId("7"), OutboundMessagePart("Alert.")
        ),
        lambda: bot.get_webhook_info(token),
        lambda: bot.send_typing_action(token, chat),
    ]

    for call in calls:
        with pytest.raises(ProviderCircuitOpenError):
            call()

    assert testbed.telegram_transport.requests == []


def test_a_closed_platform_bot_circuit_lets_the_call_through() -> None:
    testbed = ChannelsTestbed()
    testbed.telegram_transport.respond(
        "POST", r"/sendMessage$", {"ok": True, "result": {"message_id": 7}}
    )
    circuit = provider_circuit(OutboundProvider.PLATFORM_BOT)
    bot = CircuitBreakingTelegramBotAdapter(
        testbed.telegram_client, CircuitBreakerFacilitator(Ticks().clock()), circuit
    )

    sent = bot.send_message(
        ChannelSecret(PLATFORM_BOT_TOKEN),
        ChannelUserId("100200300"),
        OutboundMessagePart("Alert."),
    )

    assert sent == ProviderMessageId("100200300:7")
    assert len(testbed.telegram_transport.requests) == 1


def test_mail_sms_and_payments_wait_for_their_circuits() -> None:
    senders = RecordingSenders()
    smtp = provider_circuit(OutboundProvider.SMTP)
    twilio = provider_circuit(OutboundProvider.TWILIO_SMS)
    flitt = provider_circuit(OutboundProvider.FLITT)
    email = guard_email_sender(senders, open_breaker(smtp))
    sms = guard_sms_sender(senders, open_breaker(twilio))
    payments = CircuitBreakingPaymentGatewayAdapter(senders, open_breaker(flitt), flitt)
    assert email is not None and sms is not None

    with pytest.raises(ProviderCircuitOpenError):
        email.send_email(
            EmailAddress("owner@example.com"),
            EmailSubject("Alert"),
            EmailBodyText("Meta is down."),
            None,
        )
    with pytest.raises(ProviderCircuitOpenError):
        sms.send_sms(E164PhoneNumber("+995599000001"), SmsMessageText("Alert"))
    with pytest.raises(ProviderCircuitOpenError):
        payments.create_checkout(build_checkout_request())
    with pytest.raises(ProviderCircuitOpenError):
        payments.stop_recurring(
            PaymentProvider.FLITT, PaymentProviderReference("802345671")
        )
    # A notification is checked locally: no circuit in the way.
    with pytest.raises(LookupError):
        payments.read_notification(
            PaymentWebhookDelivery(body=PaymentWebhookBody("{}"))
        )

    assert senders.calls == ["read_notification"]
    # A provider that is not configured stays unconfigured.
    assert guard_email_sender(None, open_breaker(smtp)) is None
    assert guard_sms_sender(None, open_breaker(twilio)) is None
