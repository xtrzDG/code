"""
The channels testbed's customer media: stored voice notes and photos, the
platforms' downloads and the speech-to-text, all fakes, and the worker step
that reads a message's attachments before the turn.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.orchestrators.channels.inbox.read_inbound_attachments_orchestrator import (
    ReadInboundAttachmentsOrchestrator,
)
from app.repositories.message_media_repository import MessageMediaRepository
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.message_media import MessageMediaDocument
from app.use_cases.channels.inbox.fetch_inbound_media_use_case import (
    FetchInboundMediaUseCase,
)
from app.use_cases.conversations.transcribe_voice_note_use_case import (
    TranscribeVoiceNoteUseCase,
)
from tests.channels.channels_call_follow_ups import ChannelsCallFollowUps
from tests.media.media_fakes import (
    FakeMediaFetcher,
    FakeVoiceTranscriber,
    InMemoryMediaStorage,
)


class ChannelsMedia(ChannelsCallFollowUps):
    """Voice notes, photos and places of customer messages, read by the worker."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        super().__init__(settings)
        self.message_media_repo = MessageMediaRepository(
            InMemoryDocumentCollectionAdapter(MessageMediaDocument)
        )
        self.media_storage = InMemoryMediaStorage()
        self.media_fetcher = FakeMediaFetcher()
        self.voice_transcriber = FakeVoiceTranscriber()
        self.read_inbound_attachments = ReadInboundAttachmentsOrchestrator(
            FetchInboundMediaUseCase(
                channel_repo=self.channel_repo,
                secret_cipher=self.secret_cipher,
                media_fetcher=self.media_fetcher,
                media_storage=self.media_storage,
                message_media_repo=self.message_media_repo,
                media_settings=self.settings.media,
                wall_clock=self.wall_clock,
            ),
            TranscribeVoiceNoteUseCase(
                message_media_repo=self.message_media_repo,
                media_storage=self.media_storage,
                voice_transcriber=self.voice_transcriber,
                business_repo=self.business_repo,
                assistant_version_repo=self.assistant_version_repo,
                usage_event_repo=self.usage_event_repo,
                media_settings=self.settings.media,
                wall_clock=self.wall_clock,
            ),
        )
