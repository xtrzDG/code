import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channels import (
    ChannelAdapterContract,
    WhatsAppTemplateAdapterContract,
)
from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.repositories import ChannelRepoContract, UsageEventRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.billing import UsageEventDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels import ChannelDeliveryTarget
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.constrained_integers import UsageQuantity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.constrained_strings import (
    MetaObjectId,
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.delivery_targets import (
    build_delivery_target,
    build_whatsapp_usage_event,
    find_business_channel,
)
from app.utilities.channels.language_codes import to_whatsapp_template_language

logger: logging.Logger = logging.getLogger(__name__)

FALLBACK_TEMPLATE_LANGUAGE: WhatsAppTemplateLanguageCode = WhatsAppTemplateLanguageCode(
    "en"
)
ONE_TEMPLATE: UsageQuantity = UsageQuantity(1)


class ChannelMessageSenderFacilitator(ChannelMessageSenderFacilitatorContract):
    """
    Proactive messages to a customer (confirmation after a call, reminders)
    through the business's own connected Telegram bot, WhatsApp number,
    Messenger page or Instagram account.

    WhatsApp accepts free-form text only within 24 hours of the customer's
    last message; later messages need an approved template, sent from the
    business's own WhatsApp number in the customer's language (English
    when the template has no such translation). Every delivery is metered
    once: free-form WhatsApp text as WHATSAPP_REPLY, a template as
    WHATSAPP_TEMPLATE. Phone, web chat and other channels cannot carry
    proactive messages.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        telegram_adapter: ChannelAdapterContract,
        whatsapp_adapter: ChannelAdapterContract,
        messenger_adapter: ChannelAdapterContract,
        instagram_adapter: ChannelAdapterContract,
        whatsapp_templates: WhatsAppTemplateAdapterContract,
        usage_event_repo: UsageEventRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._adapters: dict[ChannelKind, ChannelAdapterContract] = {
            ChannelKind.TELEGRAM: telegram_adapter,
            ChannelKind.WHATSAPP: whatsapp_adapter,
            ChannelKind.MESSENGER: messenger_adapter,
            ChannelKind.INSTAGRAM: instagram_adapter,
        }
        self._whatsapp_templates: WhatsAppTemplateAdapterContract = whatsapp_templates
        self._usage_event_repo: UsageEventRepoContract = usage_event_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def send(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
        text: MessageText,
    ) -> None:
        adapter: ChannelAdapterContract | None = self._adapters.get(channel)
        if adapter is None:
            raise ExternalServiceError(
                f"Messages cannot be sent through the {channel.value} channel."
            )

        channel_document: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            business_id,
            channel,
        )
        if channel_document is None:
            raise ExternalServiceError(
                f"The {channel.value} channel of this business is not connected."
            )

        target: ChannelDeliveryTarget = build_delivery_target(
            channel_document,
            channel_user_id,
            self._secret_cipher,
        )
        delivered: DeliveredMessageCount = adapter.send(target, text)
        if channel is ChannelKind.WHATSAPP and delivered > 0:
            self._usage_event_repo.append(
                build_whatsapp_usage_event(
                    business_id,
                    None,
                    delivered,
                    self._wall_clock.now_unix(),
                )
            )

    def send_whatsapp_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language: LanguageTag,
        body_parameters: list[MessageText],
    ) -> None:
        channel_document: ChannelDocument | None = find_business_channel(
            self._channel_repo,
            business_id,
            ChannelKind.WHATSAPP,
        )
        if channel_document is None:
            raise ExternalServiceError(
                "The whatsapp channel of this business is not connected."
            )

        target: ChannelDeliveryTarget = build_delivery_target(
            channel_document,
            channel_user_id,
            self._secret_cipher,
        )
        try:
            phone_number_id = MetaObjectId(str(target.account_id))
        except ValueError as error:
            raise ExternalServiceError(
                "The WhatsApp number of this business is not connected."
            ) from error

        language_code: WhatsAppTemplateLanguageCode = to_whatsapp_template_language(
            language
        )
        try:
            self._whatsapp_templates.send_template(
                phone_number_id,
                channel_user_id,
                template_name,
                language_code,
                body_parameters,
            )
        except ExternalServiceError:
            if language_code == FALLBACK_TEMPLATE_LANGUAGE:
                raise

            logger.warning(
                "WhatsApp template %s in %s failed; retrying in English.",
                template_name,
                language_code,
            )
            self._whatsapp_templates.send_template(
                phone_number_id,
                channel_user_id,
                template_name,
                FALLBACK_TEMPLATE_LANGUAGE,
                body_parameters,
            )

        now: Microseconds = self._wall_clock.now_unix()
        self._usage_event_repo.append(
            UsageEventDocument(
                business_id=business_id,
                kind=UsageKind.WHATSAPP_TEMPLATE,
                quantity=ONE_TEMPLATE,
                occurred_at=now,
                created_at=now,
                updated_at=now,
            )
        )
