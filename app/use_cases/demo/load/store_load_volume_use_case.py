from collections.abc import Callable, Sequence
from itertools import batched

from app.contracts.load_data import LoadDatasetRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.demo_data import DemoBusinessFoundation
from app.schemas.dto.load_data import (
    LoadBusinessSeed,
    LoadVolume,
    LoadVolumeRequest,
    LoadVolumeStorage,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.channels.constrained_strings import TelegramWebhookSecret
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.demo.constrained_integers import (
    LoadBookingCount,
    LoadMessageCount,
)
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret

# Documents per write transaction.
WRITE_BATCH_SIZE: int = 1_000
# Recent conversations the manifest names per business (card requests).
MANIFEST_CONVERSATIONS: int = 20
# Channels customers chat in; the phone line has calls, not chats.
CHAT_CHANNELS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.WHATSAPP,
        ChannelKind.INSTAGRAM,
        ChannelKind.MESSENGER,
        ChannelKind.TELEGRAM,
        ChannelKind.WEB_CHAT,
        ChannelKind.VIBER,
    }
)


class StoreLoadVolumeUseCase(UseCaseContract[LoadVolumeStorage, LoadBusinessSeed]):
    """
    Last step of a load business: store its bulk history (contacts,
    conversations pinned to the published assistant version, messages and
    bookings, in batches of a thousand per transaction through the
    repositories) and describe the business as the load tests address it.

    A business with a Telegram bot gets the webhook secret token Telegram
    would send (derived from ENCRYPTION_KEY and the bot token, so webhook
    bursts pass verification).
    """

    def __init__(
        self,
        load_dataset_registry: LoadDatasetRegistryContract,
        business_repo: BusinessRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        booking_repo: BookingRepoContract,
        app_settings: AppSettings,
    ) -> None:
        self._registry: LoadDatasetRegistryContract = load_dataset_registry
        self._business_repo: BusinessRepoContract = business_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: LoadVolumeStorage) -> LoadBusinessSeed:
        foundation: DemoBusinessFoundation = input_data.plan.foundation
        business: BusinessDocument | None = self._business_repo.get(
            foundation.business.id
        )
        if business is None or business.published_assistant_version_id is None:
            raise NotFoundError("The load business has no published assistant.")

        volume: LoadVolume = self._registry.build_volume(
            LoadVolumeRequest(
                business=business,
                resources=foundation.resources,
                channel_kinds=[
                    channel.kind
                    for channel in foundation.channels
                    if channel.kind in CHAT_CHANNELS
                ],
                assistant_version_id=business.published_assistant_version_id,
                model_id=self._app_settings.llm_model_id,
                share=input_data.plan.share,
                random_seed=input_data.plan.random_seed,
                now=input_data.seeded_at,
            )
        )
        store_in_batches(volume.contacts, self._contact_repo.save_many)
        store_in_batches(volume.conversations, self._conversation_repo.save_many)
        store_in_batches(volume.messages, self._message_repo.save_many)
        store_in_batches(volume.bookings, self._booking_repo.save_many)
        telegram: ChannelDocument | None = next(
            (
                channel
                for channel in foundation.channels
                if channel.kind is ChannelKind.TELEGRAM
            ),
            None,
        )
        return LoadBusinessSeed(
            business_id=business.id,
            owner_access_token=input_data.plan.owner_access_token,
            conversation_ids=recent_conversation_ids(volume),
            visitors=volume.visitors,
            telegram_channel_id=None if telegram is None else telegram.id,
            telegram_webhook_secret=(
                None if telegram is None else self._webhook_secret(foundation)
            ),
            message_count=LoadMessageCount(len(volume.messages)),
            booking_count=LoadBookingCount(len(volume.bookings)),
        )

    def _webhook_secret(
        self, foundation: DemoBusinessFoundation
    ) -> TelegramWebhookSecret | None:
        encryption_key = self._app_settings.encryption_key
        for credential in foundation.channel_credentials:
            if credential.channel is ChannelKind.TELEGRAM and encryption_key:
                return derive_telegram_webhook_secret(encryption_key, credential.secret)

        return None


def store_in_batches[Document](
    documents: Sequence[Document],
    save_many: Callable[[Sequence[Document]], None],
) -> None:
    for batch in batched(documents, WRITE_BATCH_SIZE, strict=False):
        save_many(batch)


def recent_conversation_ids(volume: LoadVolume) -> list[ConversationId]:
    visitor_ids: set[ConversationId] = {
        visitor.conversation_id for visitor in volume.visitors
    }
    chats = sorted(
        (
            conversation
            for conversation in volume.conversations
            if conversation.id not in visitor_ids
        ),
        key=lambda conversation: int(conversation.last_message_at),
        reverse=True,
    )
    return [conversation.id for conversation in chats[:MANIFEST_CONVERSATIONS]]
