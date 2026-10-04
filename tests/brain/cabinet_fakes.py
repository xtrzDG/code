"""Fakes behind the cabinet routes: token login, the outbox, recordings."""

from dataclasses import dataclass, field

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.operator_contract import OperatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.facilitators.jobs.job_queue_facilitator import JobQueueFacilitator
from app.repositories.booking_repositories import BookingRepository, LeadRepository
from app.repositories.delivery_repositories import OutboundMessageRepository
from app.repositories.knowledge_repositories import ResourceRepository
from app.repositories.message_media_repository import MessageMediaRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.dto.mfa import SessionAssurance
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.recordings.recording_byte_ranges import cut_recording_part
from tests.foundation.access_support import signed_in
from tests.media.media_fakes import InMemoryMediaStorage
from tests.platform.worker_fakes import build_job_stores
from tests.storage.storage_testing import build_fixed_wall_clock


class TokenAuthenticationOperator(OperatorContract[AccessToken, SessionAssurance]):
    """Bearer token -> user, from a fixed table."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> SessionAssurance:
        user_id: UserId | None = self._users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return signed_in(user_id)


class CabinetOutbox:
    """
    The outbox the cabinet's staff replies go into (in memory) with the
    job queue of their deliveries; `sent` and `templates` read the queued
    messages back (no worker sends them here).
    """

    def __init__(self) -> None:
        self.messages = InMemoryDocumentCollectionAdapter(OutboundMessageDocument)
        self.outbound_message_repo = OutboundMessageRepository(self.messages)
        self.jobs = build_job_stores()
        self.job_queue = JobQueueFacilitator(
            self.jobs.job_repo, build_fixed_wall_clock(), self.jobs.job_wakeup
        )

    def queued(self) -> list[OutboundMessageDocument]:
        return sorted(self.messages.list_all(), key=lambda item: int(item.created_at))

    @property
    def sent(self) -> list[tuple[ChannelKind, str, str]]:
        """Free-text replies: channel, recipient, text."""

        return [
            (
                message.customer.channel,
                str(message.customer.channel_user_id),
                str(message.text),
            )
            for message in self.queued()
            if message.customer is not None and message.template is None
        ]

    @property
    def templates(self) -> list[tuple[str, str, str, list[str]]]:
        """Template replies: recipient, template, language, parameters."""

        return [
            (
                str(message.customer.channel_user_id),
                str(message.template.name),
                str(message.template.language_code),
                [str(value) for value in message.template.body_parameters],
            )
            for message in self.queued()
            if message.customer is not None and message.template is not None
        ]


class InMemoryRecordingStorage(RecordingStorageAdapterContract):
    """Recordings by path; `failure` makes the storage unreachable."""

    def __init__(self) -> None:
        self.recordings: dict[str, bytes] = {}
        self.reads: list[str] = []
        self.failure: str | None = None

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        self.reads.append(str(location.path))
        if self.failure is not None:
            raise ExternalServiceError(self.failure)

        content: bytes | None = self.recordings.get(str(location.path))
        if content is None:
            return None

        return cut_recording_part(
            RecordingAudio(
                content=content, media_type=RecordingMediaType("audio/mpeg")
            ),
            wanted,
        )

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        self.recordings[str(location.path)] = audio.content

    def delete(self, location: RecordingLocation) -> None:
        self.recordings.pop(str(location.path), None)


@dataclass
class CabinetStorage:
    """What the cabinet reads beside the brain world: bookings, leads, places."""

    booking_repo: BookingRepository = field(
        default_factory=lambda: BookingRepository(
            InMemoryDocumentCollectionAdapter(BookingDocument)
        )
    )
    lead_repo: LeadRepository = field(
        default_factory=lambda: LeadRepository(
            InMemoryDocumentCollectionAdapter(LeadDocument)
        )
    )
    resource_repo: ResourceRepository = field(
        default_factory=lambda: ResourceRepository(
            InMemoryDocumentCollectionAdapter(ResourceDocument)
        )
    )
    outbox: CabinetOutbox = field(default_factory=CabinetOutbox)
    recording_storage: InMemoryRecordingStorage = field(
        default_factory=InMemoryRecordingStorage
    )
    message_media_repo: MessageMediaRepository = field(
        default_factory=lambda: MessageMediaRepository(
            InMemoryDocumentCollectionAdapter(MessageMediaDocument)
        )
    )
    media_storage: InMemoryMediaStorage = field(default_factory=InMemoryMediaStorage)


class UnusedMenuExtractor:
    """Menu extractor for tests that never import a menu."""

    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        raise AssertionError("Menu extraction is not part of these tests.")


class KeepTestChatVersions(UseCaseContract[OwnerTestChatCommand, None]):
    """The test chat's preview step that never builds a version."""

    def run(self, input_data: OwnerTestChatCommand) -> None:
        del input_data
