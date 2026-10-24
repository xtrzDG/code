from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.media import (
    VoiceNoteTranscription,
    VoiceNoteTranscriptionRequest,
)
from app.schemas.dto.media_requests import InboundMediaRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId


class ReadInboundAttachmentsOrchestrator(
    OrchestratorContract[InboundMediaRequest, InboundMessage]
):
    """
    Read what a customer sent besides text, before the assistant's turn:
    download and keep the voice notes and photos (channels), then
    transcribe each voice note (conversations). The engine gets the
    message with its attachments: transcripts, stored photos, places, and
    what could not be read, which is answered with a request to write
    rather than with silence.
    """

    def __init__(
        self,
        fetch_inbound_media: UseCaseContract[
            InboundMediaRequest, list[MessageAttachment]
        ],
        transcribe_voice_note: UseCaseContract[
            VoiceNoteTranscriptionRequest, VoiceNoteTranscription
        ],
    ) -> None:
        self._fetch_inbound_media: UseCaseContract[
            InboundMediaRequest, list[MessageAttachment]
        ] = fetch_inbound_media
        self._transcribe_voice_note: UseCaseContract[
            VoiceNoteTranscriptionRequest, VoiceNoteTranscription
        ] = transcribe_voice_note

    def execute(self, input_data: InboundMediaRequest) -> InboundMessage:
        attachments: list[MessageAttachment] = self._fetch_inbound_media.run(input_data)
        business_id: BusinessId = input_data.message.business_id
        read: list[MessageAttachment] = [
            self._transcribe(business_id, attachment, input_data.is_final_attempt)
            for attachment in attachments
        ]
        return input_data.message.model_copy(update={"attachments": read})

    def _transcribe(
        self,
        business_id: BusinessId,
        attachment: MessageAttachment,
        is_final_attempt: bool,
    ) -> MessageAttachment:
        if attachment.kind is not AttachmentKind.AUDIO or attachment.problem:
            return attachment

        return self._transcribe_voice_note.run(
            VoiceNoteTranscriptionRequest(
                business_id=business_id,
                attachment=attachment,
                is_final_attempt=is_final_attempt,
            )
        ).attachment
