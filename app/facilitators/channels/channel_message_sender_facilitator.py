import logging
from collections.abc import Callable

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
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
)
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
from app.utilities.channels.channel_health import (
    mark_channel_failing,
    mark_channel_working,
    reload_same_connection,
)
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
    when the template has no such translation) or in the one language the
    owner named for it. Every delivery is metered
    once: free-form WhatsApp text as WHATSAPP_REPLY, a template as
    WHATSAPP_TEMPLATE. Phone, web chat and other channels cannot carry
    proactive messages. A platform that refuses the channel's credential
    puts the channel in ERROR (the error is raised again); a delivered
    message clears that state.
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
        try:
            delivered: DeliveredMessageCount = adapter.send(target, text)
        except ChannelCredentialRejectedError as error:
            self._record_health(channel_document, str(error))
            raise

        self._record_health(channel_document, None)
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
        language_code: WhatsAppTemplateLanguageCode = to_whatsapp_template_language(
            language
        )
        self._deliver_template(
            business_id,
            channel_user_id,
            lambda phone_number_id: self._send_template(
                phone_number_id,
                channel_user_id,
                template_name,
                language_code,
                body_parameters,
            ),
        )

    def send_whatsapp_template_in_language(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        self._deliver_template(
            business_id,
            channel_user_id,
            lambda phone_number_id: self._whatsapp_templates.send_template(
                phone_number_id,
                channel_user_id,
                template_name,
                language_code,
                body_parameters,
            ),
        )

    def _deliver_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        send: Callable[[MetaObjectId], None],
    ) -> None:
        """
        Send a template from the business's WhatsApp number, keep the
        channel's health and meter one WHATSAPP_TEMPLATE usage event.
        """

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

        try:
            send(phone_number_id)
        except ChannelCredentialRejectedError as error:
            self._record_health(channel_document, str(error))
            raise

        self._record_health(channel_document, None)
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

    def _send_template(
        self,
        phone_number_id: MetaObjectId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        """The template in the customer's language, else in English."""

        try:
            self._whatsapp_templates.send_template(
                phone_number_id,
                channel_user_id,
                template_name,
                language_code,
                body_parameters,
            )
        except ChannelCredentialRejectedError:
            raise
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

    def _record_health(
        self,
        sent_with: ChannelDocument,
        failure: str | None,
    ) -> None:
        """
        Mark the channel as it is stored now, not the copy read before the
        network call: a reconnect (or disable) while the message was in
        flight is kept, and the outcome of the old credential is ignored.
        """

        channel: ChannelDocument | None = reload_same_connection(
            self._channel_repo, sent_with
        )
        if channel is None:
            return

        now: Microseconds = self._wall_clock.now_unix()
        if failure is None:
            mark_channel_working(self._channel_repo, channel, now)
        else:
            mark_channel_failing(self._channel_repo, channel, failure, now)
