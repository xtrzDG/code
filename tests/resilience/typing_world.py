"""Real channel adapters and clients over recorded HTTP, for typing tests."""

import threading
from dataclasses import dataclass, field

from app.adapters.channels.instagram_channel_adapter import InstagramChannelAdapter
from app.adapters.channels.messenger_channel_adapter import MessengerChannelAdapter
from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.clients.meta.meta_typing_client import MetaTypingClient
from app.clients.telegram.telegram_bot_client import TelegramBotClient
from app.facilitators.channels.typing_signal_facilitator import (
    TypingSignalFacilitator,
)
from app.repositories.business_repositories import ChannelRepository
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.typing_signals import TypingRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    ProviderMessageId,
)
from app.schemas.typings.conversations.strings import ChannelUserId
from app.utilities.localization.phone_number_parser import PhoneNumberParser
from tests.channels.channels_fakes import FakeSecretCipher
from tests.channels.channels_settings import build_settings
from tests.channels.recording_transport import RecordingTransport

BOT_TOKEN: str = "123456:test-token-0000"
PAGE_TOKEN: str = "page-token-0000"
# Fast refreshes, so a test sees several signals in a fraction of a second.
FAST_REFRESH: dict[ChannelKind, float] = dict.fromkeys(ChannelKind, 0.02)


@dataclass
class TypingWorld:
    telegram: RecordingTransport = field(default_factory=RecordingTransport)
    meta: RecordingTransport = field(default_factory=RecordingTransport)
    business_id: BusinessId = field(default_factory=BusinessId)
    cipher: FakeSecretCipher = field(default_factory=FakeSecretCipher)
    channels: ChannelRepository = field(
        default_factory=lambda: ChannelRepository(
            InMemoryDocumentCollectionAdapter(ChannelDocument)
        )
    )

    def __post_init__(self) -> None:
        self.telegram.respond("POST", r"/sendChatAction$", {"ok": True, "result": True})
        self.meta.respond("POST", r"/messages$", {"success": True})
        settings = build_settings()
        meta_client = MetaGraphClient(transport=self.meta.build())
        typing_client = MetaTypingClient(transport=self.meta.build())
        self.facilitator = TypingSignalFacilitator(
            channel_repo=self.channels,
            secret_cipher=self.cipher,
            telegram_adapter=TelegramChannelAdapter(
                TelegramBotClient(transport=self.telegram.build()),
                PhoneNumberParser(),
                settings,
            ),
            whatsapp_adapter=WhatsAppChannelAdapter(
                meta_client, PhoneNumberParser(), settings, typing_client
            ),
            messenger_adapter=MessengerChannelAdapter(
                meta_client, settings, typing_client
            ),
            instagram_adapter=InstagramChannelAdapter(
                meta_client, settings, typing_client
            ),
            refresh_seconds=FAST_REFRESH,
        )
        self._threads_before: set[threading.Thread] = set(threading.enumerate())

    def facilitator_threads_stopped(self) -> bool:
        """No typing thread started since this world was made still runs."""

        return not any(
            thread.name.startswith("typing-") and thread.is_alive()
            for thread in set(threading.enumerate()) - self._threads_before
        )

    def connect(
        self,
        kind: ChannelKind,
        external_id: str,
        secret: str | None = None,
        business_id: BusinessId | None = None,
    ) -> ChannelDocument:
        channel = ChannelDocument(
            business_id=self.business_id if business_id is None else business_id,
            kind=kind,
            external_id=ChannelExternalId(external_id),
            encrypted_secret=(
                None if secret is None else self.cipher.encrypt(ChannelSecret(secret))
            ),
            status=ChannelStatus.CONNECTED,
        )
        self.channels.save(channel)
        return channel

    def request(
        self,
        channel: ChannelDocument,
        user_id: str = "42",
        replying_to: str | None = None,
    ) -> TypingRequest:
        return TypingRequest(
            business_id=self.business_id,
            channel=channel.kind,
            channel_id=channel.id,
            channel_user_id=ChannelUserId(user_id),
            replying_to=(
                None if replying_to is None else ProviderMessageId(replying_to)
            ),
        )
