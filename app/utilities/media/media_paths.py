"""Where a customer file is kept, and the ids that make a retry find it."""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId
from app.schemas.typings.media.strings import MediaStoragePath

MESSAGE_MEDIA_NAMESPACE: UUID = UUID("6f1d3c2a-8b5e-4f7a-9c1d-2e3f4a5b6c7d")
MEDIA_DIRECTORY: str = "message-media"
FILE_EXTENSIONS: dict[str, str] = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "audio/amr": "amr",
    "audio/wav": "wav",
    "audio/webm": "webm",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
DEFAULT_EXTENSION: str = "bin"


def derive_message_media_id(event_id: InboundEventId, position: int) -> MessageMediaId:
    """The same attachment of the same inbox event: the same stored file."""

    return MessageMediaId(uuid5(MESSAGE_MEDIA_NAMESPACE, f"{event_id}|{position}"))


def media_storage_path(
    business_id: BusinessId,
    media_id: MessageMediaId,
    media_type: MessageMediaType,
) -> MediaStoragePath:
    """`message-media/<business>/<media id>.<extension of its type>`."""

    extension: str = FILE_EXTENSIONS.get(str(media_type), DEFAULT_EXTENSION)
    return MediaStoragePath(f"{MEDIA_DIRECTORY}/{business_id}/{media_id}.{extension}")


def media_type_of_extension(file_name: str) -> MessageMediaType | None:
    """The media type a stored file's extension stands for (local storage)."""

    extension: str = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    for media_type, known_extension in FILE_EXTENSIONS.items():
        if known_extension == extension:
            return MessageMediaType(media_type)

    return None
