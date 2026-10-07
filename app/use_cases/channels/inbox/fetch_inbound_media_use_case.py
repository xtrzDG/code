import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.channel_media import ChannelMediaFetcherContract
from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.constants.media import AttachmentKind, AttachmentProblem
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.message_media import (
    InboundAttachment,
    MessageAttachment,
    MessageMediaDocument,
)
from app.schemas.dto.media import (
    ChannelMediaRequest,
    FetchedMedia,
    MediaLocation,
    StoredMediaFile,
)
from app.schemas.dto.media_requests import InboundMediaRequest
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
    MediaByteLimit,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.utilities.channels.delivery_targets import decrypt_channel_secret
from app.utilities.media.attachment_files import (
    attachment_of_stored_media,
    unreadable_attachment,
)
from app.utilities.media.audio_duration import read_audio_duration_seconds
from app.utilities.media.media_paths import derive_message_media_id, media_storage_path
from app.utilities.media.media_sniffing import kind_of_media_type, sniff_media_type

logger: logging.Logger = logging.getLogger(__name__)
FILE_KINDS: frozenset[AttachmentKind] = frozenset(
    {AttachmentKind.AUDIO, AttachmentKind.IMAGE}
)


class FetchInboundMediaUseCase(
    UseCaseContract[InboundMediaRequest, list[MessageAttachment]]
):
    """
    Download and keep the files of a customer message (in the worker, after
    the webhook was acknowledged).

    Each voice note and photo is downloaded from its platform (at most
    MEDIA_MAX_VOICE_BYTES or MEDIA_MAX_IMAGE_BYTES; a declared size over
    the cap is refused before the download), recognized from its bytes
    (only audio and the pictures a model reads are kept), stored encrypted
    with the business's key and recorded as a `MessageMediaDocument`, whose
    id is derived from the event: a turn that runs again finds what it
    stored. A place is read as it came; every other kind is kept as one the
    assistant cannot read. A file the platform does not hand out is given
    up (UNAVAILABLE); a temporary failure fails the job to try again, and
    only its last attempt gives the file up.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        secret_cipher: SecretCipherAdapterContract,
        media_fetcher: ChannelMediaFetcherContract,
        media_storage: MediaStorageAdapterContract,
        message_media_repo: MessageMediaRepoContract,
        media_settings: MediaSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher
        self._media_fetcher: ChannelMediaFetcherContract = media_fetcher
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._message_media_repo: MessageMediaRepoContract = message_media_repo
        self._media_settings: MediaSettings = media_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: InboundMediaRequest) -> list[MessageAttachment]:
        event: InboundEventDocument = input_data.event
        inbound: list[InboundAttachment] = (
            [] if event.customer_message is None else event.customer_message.attachments
        )
        if event.business_id is None or not inbound:
            return []

        credential: ChannelSecret | None = self._read_credential(event)
        return [
            self._read(
                event, event.business_id, position, attachment, credential, input_data
            )
            for position, attachment in enumerate(inbound)
        ]

    def _read(
        self,
        event: InboundEventDocument,
        business_id: BusinessId,
        position: int,
        attachment: InboundAttachment,
        credential: ChannelSecret | None,
        request: InboundMediaRequest,
    ) -> MessageAttachment:
        if attachment.kind is AttachmentKind.LOCATION and attachment.location:
            return MessageAttachment(kind=attachment.kind, location=attachment.location)

        if attachment.kind not in FILE_KINDS:
            return unreadable_attachment(attachment, AttachmentProblem.UNSUPPORTED_KIND)

        media_id: MessageMediaId = derive_message_media_id(event.id, position)
        stored: MessageMediaDocument | None = self._message_media_repo.get(
            business_id, media_id
        )
        if stored is not None:
            return attachment_of_stored_media(stored)

        limit: MediaByteLimit = (
            self._media_settings.max_voice_bytes
            if attachment.kind is AttachmentKind.AUDIO
            else self._media_settings.max_image_bytes
        )
        if attachment.provider_media_id is None:
            return unreadable_attachment(attachment, AttachmentProblem.UNAVAILABLE)

        if attachment.declared_bytes is not None and int(
            attachment.declared_bytes
        ) > int(limit):
            return unreadable_attachment(attachment, AttachmentProblem.TOO_LARGE)

        try:
            fetched: FetchedMedia = self._media_fetcher.fetch(
                ChannelMediaRequest(
                    channel=event.channel,
                    provider_media_id=attachment.provider_media_id,
                    credential=credential,
                    max_bytes=limit,
                )
            )
        except MediaTooLargeError:
            return unreadable_attachment(attachment, AttachmentProblem.TOO_LARGE)
        except MediaUnavailableError as error:
            logger.warning("A %s file is unavailable: %s", event.channel.value, error)
            return unreadable_attachment(attachment, AttachmentProblem.UNAVAILABLE)
        except ExternalServiceError:
            if not request.is_final_attempt:
                raise

            logger.exception("A %s file could not be fetched.", event.channel.value)
            return unreadable_attachment(attachment, AttachmentProblem.UNAVAILABLE)

        return self._keep(event, business_id, media_id, attachment, fetched)

    def _keep(
        self,
        event: InboundEventDocument,
        business_id: BusinessId,
        media_id: MessageMediaId,
        attachment: InboundAttachment,
        fetched: FetchedMedia,
    ) -> MessageAttachment:
        media_type: MessageMediaType | None = sniff_media_type(fetched.content)
        if media_type is None or kind_of_media_type(media_type) is not attachment.kind:
            return unreadable_attachment(
                attachment, AttachmentProblem.UNRECOGNIZED_FORMAT
            )

        location = MediaLocation(
            business_id=business_id,
            path=media_storage_path(business_id, media_id, media_type),
        )
        self._media_storage.store(
            location, StoredMediaFile(content=fetched.content, media_type=media_type)
        )
        now: Microseconds = self._wall_clock.now_unix()
        measured: int | None = (
            read_audio_duration_seconds(fetched.content)
            if attachment.kind is AttachmentKind.AUDIO
            else None
        )
        media = MessageMediaDocument(
            id=media_id,
            business_id=business_id,
            message_id=event.customer_message_id,
            kind=attachment.kind,
            storage_path=location.path,
            media_type=media_type,
            byte_count=MediaByteCount(len(fetched.content)),
            duration_seconds=attachment.duration_seconds
            or (None if measured is None else AudioDurationSeconds(measured)),
            created_at=now,
            updated_at=now,
        )
        self._message_media_repo.save(media)
        return attachment_of_stored_media(media)

    def _read_credential(self, event: InboundEventDocument) -> ChannelSecret | None:
        """The channel's bot or page token (Telegram, Messenger, Instagram)."""

        channel: ChannelDocument | None = (
            None
            if event.channel_id is None
            else self._channel_repo.get(event.channel_id)
        )
        if channel is None or channel.business_id != event.business_id:
            return None

        return decrypt_channel_secret(channel, self._secret_cipher)
