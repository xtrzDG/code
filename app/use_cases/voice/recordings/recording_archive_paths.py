"""Where the platform keeps a call recording it archived from the voice platform."""

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.channels.voice_recordings import RECORDING_MEDIA_TYPES_BY_EXTENSION

ARCHIVE_CALL_RECORDING_JOB: JobName = JobName("archive_call_recording")
DEFAULT_EXTENSION: str = ".mp3"


def build_archived_recording_path(
    business_id: BusinessId,
    call_id: CallId,
    media_type: RecordingMediaType,
) -> RecordingStoragePath:
    """
    "businesses/<business>/calls/<call>.<extension>": one prefix per
    business (a whole business's recordings can be listed and removed
    together), the extension of the audio's type.
    """

    extensions: dict[RecordingMediaType, str] = {}
    for known_extension, known_type in RECORDING_MEDIA_TYPES_BY_EXTENSION.items():
        extensions.setdefault(known_type, known_extension)
    extension: str = extensions.get(media_type, DEFAULT_EXTENSION)
    return RecordingStoragePath(f"businesses/{business_id}/calls/{call_id}{extension}")
