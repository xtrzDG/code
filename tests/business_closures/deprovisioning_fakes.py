"""Fakes of the providers a business's deletion switches off."""

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext

from app.contracts.billing import PaymentGatewayAdapterContract
from app.contracts.channel_clients import ProviderToken, TelegramBotApiClientContract
from app.contracts.channel_deprovisioning import MetaSubscriptionClientContract
from app.contracts.phone_numbers import (
    PhoneLineLockRegistryContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.billing_repositories import SubscriptionRepoContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.operations.calendar_connection import (
    CalendarDisconnectResult,
    DisconnectCalendarCommand,
)
from app.schemas.dto.phone_numbers.provisioning import PhoneNumberRelease
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.strings import PaymentProviderReference
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.schemas.typings.meta_connection.constrained_strings import (
    WhatsAppBusinessAccountId,
)
from app.schemas.typings.telephony.prefixed_id import PhoneNumberId

UNREADABLE: str = "unreadable"


class Cipher(SecretCipherAdapterContract):
    def decrypt(self, encrypted_secret: EncryptedChannelSecret) -> ChannelSecret:
        if str(encrypted_secret) == UNREADABLE:
            raise ExternalServiceError("The credential cannot be read.")
        return ChannelSecret(f"plain-{encrypted_secret}")


class Telegram(TelegramBotApiClientContract):
    def __init__(self, failing: bool = False) -> None:
        self.removed: list[str] = []
        self.failing: bool = failing

    def delete_webhook(self, bot_token: ProviderToken) -> None:
        if self.failing:
            raise ExternalServiceError("Telegram is down.")
        self.removed.append(str(bot_token))


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


class Channels(ChannelRepoContract):
    def __init__(self, channels: list[ChannelDocument]) -> None:
        self.channels: list[ChannelDocument] = channels

    def list_by_business(self, business_id: BusinessId) -> list[ChannelDocument]:
        return [
            channel for channel in self.channels if channel.business_id == business_id
        ]


class Versions(AssistantVersionRepoContract):
    def __init__(self, versions: list[AssistantVersionDocument]) -> None:
        self.versions: list[AssistantVersionDocument] = versions

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[AssistantVersionDocument]:
        return list(self.versions)


class RemoveVoiceAgents(UseCaseContract[BusinessId, None]):
    """Forgets the agents, or keeps them as a platform that cannot be reached."""

    def __init__(self, versions: Versions, reachable: bool) -> None:
        self._versions: Versions = versions
        self._reachable: bool = reachable

    def run(self, input_data: BusinessId) -> None:
        if self._reachable:
            self._versions.versions = [
                version.model_copy(update={"voice_agent_id": None})
                for version in self._versions.versions
            ]


class DisconnectCalendar(
    UseCaseContract[DisconnectCalendarCommand, CalendarDisconnectResult]
):
    def __init__(self, was_connected: bool) -> None:
        self._was_connected: bool = was_connected

    def run(self, input_data: DisconnectCalendarCommand) -> CalendarDisconnectResult:
        return CalendarDisconnectResult(
            business_id=input_data.business_id, was_connected=self._was_connected
        )


class PhoneNumbers(PhoneNumberRepoContract):
    def __init__(self, held: PhoneNumberDocument | None) -> None:
        self.held: PhoneNumberDocument | None = held

    def find_held(self, business_id: BusinessId) -> PhoneNumberDocument | None:
        return self.held

    def modify(
        self,
        business_id: BusinessId,
        number_id: PhoneNumberId,
        change: Callable[[PhoneNumberDocument], PhoneNumberDocument | None],
    ) -> PhoneNumberDocument | None:
        if self.held is None:
            return None
        self.held = change(self.held)
        return self.held


class Provisioner(PhoneNumberProvisionerAdapterContract):
    def __init__(self, refusing: bool = False) -> None:
        self.released: list[str] = []
        self.refusing: bool = refusing

    def release_number(self, release: PhoneNumberRelease) -> None:
        if self.refusing:
            raise ExternalServiceError("The carrier refused.")
        self.released.append(str(release.provider_number_id))


class Lock(PhoneLineLockRegistryContract):
    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        return nullcontext(object())


class Subscriptions(SubscriptionRepoContract):
    def __init__(self, subscriptions: list[SubscriptionDocument]) -> None:
        self.subscriptions: list[SubscriptionDocument] = subscriptions

    def list_by_business(self, business_id: BusinessId) -> list[SubscriptionDocument]:
        return list(self.subscriptions)


class Gateway(PaymentGatewayAdapterContract):
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
