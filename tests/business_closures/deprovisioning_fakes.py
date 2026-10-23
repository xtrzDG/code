"""Fakes of the providers a business's deletion switches off."""

from contextlib import AbstractContextManager, nullcontext

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.contracts.phone_numbers import PhoneLineLockRegistryContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.payments import PaymentProvider
from app.schemas.dto.channels.provider_profiles import (
    TelegramBotProfile,
    TelegramWebhookInfo,
)
from app.schemas.dto.operations.calendar_connection import (
    CalendarDisconnectResult,
    DisconnectCalendarCommand,
)
from app.schemas.dto.payment_retries import PaymentRetryRequest, PaymentRetryResult
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    PaymentWebhookDelivery,
    VerifiedPaymentEvent,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    ChannelWebhookUrl,
    TelegramBotUserId,
    TelegramWebhookSecret,
)
from app.schemas.typings.channels.strings import (
    OutboundMessagePart,
    ProviderMessageId,
    TelegramCallbackQueryId,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.media.strings import ProviderMediaId
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.utilities.channels.json_values import JsonObject


class Telegram(TelegramBotApiClientContract):
    """Records the bots whose webhook went; only that call is expected."""

    def __init__(self, failing: bool = False) -> None:
        self.removed: list[str] = []
        self.failing: bool = failing

    def delete_webhook(self, bot_token: ProviderToken) -> None:
        if self.failing:
            raise ExternalServiceError("Telegram is down.")
        self.removed.append(str(bot_token))

    def get_me(self, bot_token: ProviderToken) -> TelegramBotProfile:
        raise NotImplementedError

    def get_profile_photo_file_id(
        self, bot_token: ProviderToken, bot_user_id: TelegramBotUserId
    ) -> ProviderMediaId | None:
        raise NotImplementedError

    def set_webhook(
        self,
        bot_token: ProviderToken,
        url: ChannelWebhookUrl,
        secret_token: TelegramWebhookSecret,
    ) -> None:
        raise NotImplementedError

    def send_message(
        self,
        bot_token: ProviderToken,
        chat_id: ChannelUserId,
        text: OutboundMessagePart,
        reply_markup: JsonObject | None = None,
    ) -> ProviderMessageId | None:
        raise NotImplementedError

    def answer_callback_query(
        self, bot_token: ProviderToken, callback_query_id: TelegramCallbackQueryId
    ) -> None:
        raise NotImplementedError

    def edit_message_text(
        self,
        bot_token: ProviderToken,
        message_id: ProviderMessageId,
        text: OutboundMessagePart,
    ) -> None:
        raise NotImplementedError

    def get_webhook_info(self, bot_token: ProviderToken) -> TelegramWebhookInfo:
        raise NotImplementedError

    def send_typing_action(
        self, bot_token: ProviderToken, chat_id: ChannelUserId
    ) -> None:
        raise NotImplementedError


class MetaSubscriptions(MetaSubscriptionClientContract):
    def __init__(self) -> None:
        self.pages: list[str] = []
        self.accounts: list[str] = []

    def unsubscribe_page(self, page_token: ProviderToken) -> None:
        self.pages.append(str(page_token))

    def unsubscribe_whatsapp_business_account(
        self,
        access_token: ProviderToken,
        business_account_id: WhatsAppBusinessAccountId,
    ) -> None:
        self.accounts.append(str(business_account_id))


class RemoveVoiceAgents(UseCaseContract[BusinessId, None]):
    """Forgets the agents, or keeps them as a platform that cannot be reached."""

    def __init__(self, versions: AssistantVersionRepoContract, reachable: bool) -> None:
        self._versions: AssistantVersionRepoContract = versions
        self._reachable: bool = reachable

    def run(self, input_data: BusinessId) -> None:
        if not self._reachable:
            return

        for version in self._versions.list_by_business(input_data):
            self._versions.modify(
                input_data,
                version.id,
                lambda stored: stored.model_copy(update={"voice_agent_id": None}),
            )


class DisconnectCalendar(
    UseCaseContract[DisconnectCalendarCommand, CalendarDisconnectResult]
):
    def __init__(self, was_connected: bool) -> None:
        self._was_connected: bool = was_connected

    def run(self, input_data: DisconnectCalendarCommand) -> CalendarDisconnectResult:
        return CalendarDisconnectResult(
            business_id=input_data.business_id, was_connected=self._was_connected
        )


class Lock(PhoneLineLockRegistryContract):
    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        return nullcontext(object())


class Gateway(PaymentGatewayAdapterContract):
    """Records the charges stopped; only that call is expected."""

    def __init__(self, failure: ExternalServiceError | None = None) -> None:
        self.stopped: list[str] = []
        self.failure: ExternalServiceError | None = failure

    def stop_recurring(
        self,
        provider: PaymentProvider,
        provider_reference: PaymentProviderReference,
    ) -> None:
        if self.failure is not None:
            raise self.failure
        self.stopped.append(f"{provider.value}:{provider_reference}")

    def create_checkout(
        self, request: PaymentCheckoutRequest
    ) -> PaymentCheckoutSession:
        raise NotImplementedError

    def read_notification(
        self, delivery: PaymentWebhookDelivery
    ) -> VerifiedPaymentEvent:
        raise NotImplementedError

    def retry_charge(self, request: PaymentRetryRequest) -> PaymentRetryResult:
        raise NotImplementedError
