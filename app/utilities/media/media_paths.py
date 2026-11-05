"""Where a customer file is kept, and the ids that make a retry find it."""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import MessageMediaId, WidgetUploadId
from app.schemas.typings.media.strings import MediaStoragePath

MESSAGE_MEDIA_NAMESPACE: UUID = UUID("6f1d3c2a-8b5e-4f7a-9c1d-2e3f4a5b6c7d")
MEDIA_DIRECTORY: str = "message-media"
WIDGET_UPLOAD_DIRECTORY: str = "widget-uploads"
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


def widget_upload_storage_path(
    business_id: BusinessId,
    upload_id: WidgetUploadId,
    media_type: MessageMediaType,
) -> MediaStoragePath:
    """`widget-uploads/<business>/<upload id>.<extension of its type>`."""

    extension: str = FILE_EXTENSIONS.get(str(media_type), DEFAULT_EXTENSION)
    return MediaStoragePath(
        f"{WIDGET_UPLOAD_DIRECTORY}/{business_id}/{upload_id}.{extension}"
    )


def is_widget_upload_path(business_id: BusinessId, path: str) -> bool:
    """A path the widget upload of this business would have (never another's)."""

    directory: str = f"{WIDGET_UPLOAD_DIRECTORY}/{business_id}/"
    name: str = path.removeprefix(directory)
    return (
        path.startswith(directory)
        and name != ""
        and "/" not in name
        and ".." not in name
    )


def widget_upload_id_of_path(
    business_id: BusinessId, path: str
) -> WidgetUploadId | None:
    """The upload a widget upload path of this business names, else None."""

    if not is_widget_upload_path(business_id, path):
        return None

    stem: str = path.rsplit("/", 1)[-1].split(".", 1)[0]
    try:
        return WidgetUploadId(stem)
    except ValueError:
        return None


def media_type_of_extension(file_name: str) -> MessageMediaType | None:
    """The media type a stored file's extension stands for (local storage)."""

    extension: str = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    for media_type, known_extension in FILE_EXTENSIONS.items():
        if known_extension == extension:
            return MessageMediaType(media_type)

    return None
