"""Fakes behind the cabinet routes: token login, channel sender, recordings."""

from dataclasses import dataclass, field

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.booking_repositories import BookingRepository, LeadRepository
from app.repositories.knowledge_repositories import ResourceRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatCommand
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    ExternalServiceError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    MessageText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.recordings.recording_byte_ranges import cut_recording_part


class TokenAuthenticationOperator(OperatorContract[AccessToken, UserId]):
    """Bearer token -> user, from a fixed table."""

    def __init__(self, users_by_token: dict[str, UserId]) -> None:
        self._users_by_token: dict[str, UserId] = users_by_token

    def operate(self, input_data: AccessToken) -> UserId:
        user_id: UserId | None = self._users_by_token.get(str(input_data))
        if user_id is None:
            raise AuthenticationRequiredError("Unknown token.")

        return user_id


class RecordingChannelSender(ChannelMessageSenderFacilitatorContract):
    """Records messages to customers; `failure` makes the channel fail."""

    def __init__(self) -> None:
        self.sent: list[tuple[ChannelKind, str, str]] = []
        self.templates: list[tuple[str, str, str, list[str]]] = []
        self.failure: str | None = None
        self.template_rejection: str | None = None

    def send(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
        text: MessageText,
    ) -> None:
        if self.failure is not None:
            raise ExternalServiceError(self.failure)

        self.sent.append((channel, str(channel_user_id), str(text)))

    def send_whatsapp_template(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language: LanguageTag,
        body_parameters: list[MessageText],
    ) -> None:
        raise AssertionError("Staff templates are sent in their own language.")

    def send_whatsapp_template_in_language(
        self,
        business_id: BusinessId,
        channel_user_id: ChannelUserId,
        template_name: WhatsAppTemplateName,
        language_code: WhatsAppTemplateLanguageCode,
        body_parameters: list[MessageText],
    ) -> None:
        if self.failure is not None:
            raise ExternalServiceError(self.failure)

        if self.template_rejection is not None:
            raise WhatsAppTemplateRejectedError(self.template_rejection)

        self.templates.append(
            (
                str(channel_user_id),
                str(template_name),
                str(language_code),
                [str(parameter) for parameter in body_parameters],
            )
        )


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
    channel_sender: RecordingChannelSender = field(
        default_factory=RecordingChannelSender
    )
    recording_storage: InMemoryRecordingStorage = field(
        default_factory=InMemoryRecordingStorage
    )


class UnusedMenuExtractor:
    """Menu extractor for tests that never import a menu."""

    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        raise AssertionError("Menu extraction is not part of these tests.")


class KeepTestChatVersions(UseCaseContract[OwnerTestChatCommand, None]):
    """The test chat's preview step that never builds a version."""

    def run(self, input_data: OwnerTestChatCommand) -> None:
        del input_data
