import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.media_repositories import WidgetUploadRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.media_settings import MediaSettings
from app.schemas.constants.media import AttachmentKind, WidgetUploadRefusal
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.channels.widget_uploads import (
    WidgetAttachmentView,
    WidgetUploadCommand,
)
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.exceptions.media_errors import MalformedMediaFileError
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
    MediaByteLimit,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.utilities.channels.widget_visitors import widget_visitor_id
from app.utilities.media.media_paths import widget_upload_storage_path
from app.utilities.media.media_sniffing import sniff_media_type
from app.utilities.media.upload_checks import (
    measure_voice_note,
    read_declared_type,
    strip_image_metadata,
    upload_kind_of,
)
from app.utilities.media.upload_refusals import upload_refused

logger: logging.Logger = logging.getLogger(__name__)


class AcceptWidgetUploadUseCase(
    UseCaseContract[WidgetUploadCommand, WidgetAttachmentView]
):
    """
    Keep a photo or voice note a website visitor uploaded (after
    `AdmitWidgetUploadUseCase` counted it), for their next message to name.

    The file is untrusted: the type its browser declared must be a photo
    (JPEG, PNG, WebP) or a voice note (WebM, Ogg, MP4) and its own first
    bytes must say the same type (422 `unsupported_type`,
    `type_mismatch`); it must be within the cap of its kind
    (MEDIA_MAX_IMAGE_BYTES, MEDIA_MAX_VOICE_BYTES: `file_too_large`); a
    voice note must hold audio only and its length, read from its
    container, must be at most MEDIA_MAX_VOICE_SECONDS (`voice_too_long`,
    or `unreadable_file` when it cannot be read); a photo is kept without
    its metadata (`unreadable_file` when its structure does not add up).
    The file goes to the media storage, encrypted with the business's key,
    and is bound to the visitor (a one-way id of their key): another
    visitor's message cannot name it.
    """

    def __init__(
        self,
        widget_upload_repo: WidgetUploadRepoContract,
        media_storage: MediaStorageAdapterContract,
        media_settings: MediaSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._widget_upload_repo: WidgetUploadRepoContract = widget_upload_repo
        self._media_storage: MediaStorageAdapterContract = media_storage
        self._media_settings: MediaSettings = media_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetUploadCommand) -> WidgetAttachmentView:
        media_type, kind = self._recognize(input_data)
        content: bytes = input_data.content
        limit: MediaByteLimit = (
            self._media_settings.max_image_bytes
            if kind is AttachmentKind.IMAGE
            else self._media_settings.max_voice_bytes
        )
        if len(content) > int(limit):
            raise upload_refused(WidgetUploadRefusal.FILE_TOO_LARGE, limit)

        duration: AudioDurationSeconds | None = None
        if kind is AttachmentKind.AUDIO:
            duration = self._measure(content, media_type)
        else:
            content = self._without_metadata(content, media_type)

        return self._keep(input_data, kind, media_type, content, duration)

    def _recognize(
        self, input_data: WidgetUploadCommand
    ) -> tuple[MessageMediaType, AttachmentKind]:
        declared: str | None = read_declared_type(input_data.declared_type)
        sniffed: MessageMediaType | None = sniff_media_type(input_data.content)
        declared_kind: AttachmentKind | None = upload_kind_of(declared)
        if declared_kind is None:
            raise upload_refused(WidgetUploadRefusal.UNSUPPORTED_TYPE, declared)

        if sniffed is None or str(sniffed) != declared:
            raise upload_refused(WidgetUploadRefusal.TYPE_MISMATCH, declared)

        return sniffed, declared_kind

    def _measure(
        self, content: bytes, media_type: MessageMediaType
    ) -> AudioDurationSeconds:
        seconds: int | None = measure_voice_note(content, media_type)
        if seconds is None or seconds <= 0:
            raise upload_refused(WidgetUploadRefusal.UNREADABLE_FILE, media_type)

        if seconds > int(self._media_settings.max_voice_seconds):
            raise upload_refused(
                WidgetUploadRefusal.VOICE_TOO_LONG,
                self._media_settings.max_voice_seconds,
            )

        return AudioDurationSeconds(seconds)

    def _without_metadata(self, content: bytes, media_type: MessageMediaType) -> bytes:
        try:
            return strip_image_metadata(content, media_type)
        except MalformedMediaFileError as error:
            raise upload_refused(
                WidgetUploadRefusal.UNREADABLE_FILE, media_type
            ) from error

    def _keep(
        self,
        input_data: WidgetUploadCommand,
        kind: AttachmentKind,
        media_type: MessageMediaType,
        content: bytes,
        duration: AudioDurationSeconds | None,
    ) -> WidgetAttachmentView:
        now: Microseconds = self._wall_clock.now_unix()
        upload_id = WidgetUploadId()
        location = MediaLocation(
            business_id=input_data.business_id,
            path=widget_upload_storage_path(
                input_data.business_id, upload_id, media_type
            ),
        )
        upload = WidgetUploadDocument(
            id=upload_id,
            business_id=input_data.business_id,
            visitor_id=widget_visitor_id(str(input_data.session_key)),
            kind=kind,
            media_type=media_type,
            storage_path=location.path,
            byte_count=MediaByteCount(len(content)),
            duration_seconds=duration,
            created_at=now,
            updated_at=now,
        )
        self._media_storage.store(
            location, StoredMediaFile(content=content, media_type=media_type)
        )
        try:
            self._widget_upload_repo.save(upload)
        except Exception:
            # No record names the file: take it back rather than leave it.
            self._media_storage.delete(location)
            raise

        return WidgetAttachmentView(
            attachment_id=upload.id,
            kind=kind,
            media_type=media_type,
            byte_count=upload.byte_count,
            duration_seconds=duration,
        )
