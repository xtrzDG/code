"""
A message to a customer outside the 24-hour messaging window: the owner's
approved WhatsApp template from the business's number (a request for
feedback after a visit), in the customer's language, or in English when
Meta has no such translation of the template. Metered as one template.
"""

from typed_time_provider import Microseconds

from app.contracts.channels import WhatsAppTemplateAdapterContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.exceptions.application_errors import (
    ProviderRejectedMessageError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
)
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.channels.outbox.outbound_routes import OutboundRoute
from app.utilities.channels.channel_health import is_channel_active

FALLBACK_TEMPLATE_LANGUAGE: WhatsAppTemplateLanguageCode = WhatsAppTemplateLanguageCode(
    "en"
)
ONE_TEMPLATE: UsageQuantity = UsageQuantity(1)


def route_customer_template(
    message: OutboundMessageDocument,
    recipient: CustomerRecipient,
    template: OutboundTemplate,
    channel_repo: ChannelRepoContract,
    whatsapp_templates: WhatsAppTemplateAdapterContract,
) -> OutboundRoute:
    """
    One template message from the business's WhatsApp number as it is
    now. Raises ValidationFailedError when it is not a WhatsApp message or
    the number was disconnected.
    """

    channel: ChannelDocument | None = channel_repo.get(recipient.channel_id)
    if (
        recipient.channel is not ChannelKind.WHATSAPP
        or channel is None
        or channel.business_id != message.business_id
        or not is_channel_active(channel)
    ):
        raise ValidationFailedError(
            "The WhatsApp number of this business is no longer connected."
        )

    try:
        phone_number_id = MetaObjectId(str(channel.external_id))
    except ValueError as error:
        raise ValidationFailedError(
            "The WhatsApp number of this business is not connected."
        ) from error

    parameters: list[MessageText] = list(template.body_parameters) or [message.text]

    def send_part(part: MessageText) -> ProviderMessageId | None:
        del part
        try:
            return whatsapp_templates.send_template(
                phone_number_id,
                recipient.channel_user_id,
                template.name,
                template.language_code,
                parameters,
            )
        except ProviderRejectedMessageError:
            if template.language_code == FALLBACK_TEMPLATE_LANGUAGE:
                raise

            return whatsapp_templates.send_template(
                phone_number_id,
                recipient.channel_user_id,
                template.name,
                FALLBACK_TEMPLATE_LANGUAGE,
                parameters,
            )

    return OutboundRoute(parts=[message.text], send_part=send_part, channel=channel)


def build_template_usage_event(
    message: OutboundMessageDocument,
    occurred_at: Microseconds,
) -> UsageEventDocument:
    """One WhatsApp template sent (concept usage_events wa_template)."""

    return UsageEventDocument(
        business_id=message.business_id,
        conversation_id=message.conversation_id,
        kind=UsageKind.WHATSAPP_TEMPLATE,
        quantity=ONE_TEMPLATE,
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
