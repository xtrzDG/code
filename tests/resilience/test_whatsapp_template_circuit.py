"""
A WhatsApp template sent behind Meta's circuit keeps the number's own token:
a number connected through Embedded Signup (1212) sends with the business's
token, the platform's numbers with the system user's (no credential).
"""

from app.adapters.channels.circuit_breaking_whatsapp_template_adapter import (
    CircuitBreakingWhatsAppTemplateAdapter,
)
from app.contracts.channels import WhatsAppTemplateAdapterContract
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.resilience import OutboundProvider
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import ChannelSecret, ProviderMessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.utilities.resilience.provider_circuits import provider_circuit
from tests.resilience.test_circuit_breaker import Ticks


class RecordingTemplates(WhatsAppTemplateAdapterContract):
    """Templates that remember the credential each one was sent with."""

    def __init__(self) -> None:
        self.credentials: list[ChannelSecret | None] = []

    def send_template(
        self,
        phone_number_id: MetaObjectId,
        recipient: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
        credential: ChannelSecret | None = None,
    ) -> ProviderMessageId | None:
        del phone_number_id, recipient, template_name, language_code
        del body_parameters
        self.credentials.append(credential)
        return ProviderMessageId(f"wamid.{len(self.credentials)}")


def send(
    templates: CircuitBreakingWhatsAppTemplateAdapter,
    credential: ChannelSecret | None = None,
) -> ProviderMessageId | None:
    return templates.send_template(
        MetaObjectId("106540352242922"),
        ChannelUserId("995599000001"),
        WhatsAppTemplateName("booking_reminder"),
        WhatsAppTemplateLanguageCode("ka"),
        [MessageText("Salobie Bia")],
        credential,
    )


def test_a_template_behind_the_circuit_keeps_the_numbers_own_token() -> None:
    inner = RecordingTemplates()
    meta = provider_circuit(OutboundProvider.META)
    templates = CircuitBreakingWhatsAppTemplateAdapter(
        inner, CircuitBreakerFacilitator(Ticks().clock()), meta
    )

    business_token = ChannelSecret("EAAG-business-token")
    assert send(templates, business_token) == ProviderMessageId("wamid.1")
    assert send(templates) == ProviderMessageId("wamid.2")

    assert inner.credentials == [business_token, None]
