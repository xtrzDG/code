"""One call's recording as a full export lists it (recordings.json)."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.privacy import ArchivedRecordingStatus
from app.schemas.typings.conversations.constrained_integers import RecordingByteCount
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.prefixed_id import CallId, ConversationId
from app.schemas.typings.privacy.constrained_strings import (
    ArchivedRecordingFile,
    CallRecordingDownloadPath,
)


class ArchivedRecording(ImmutableDTO):
    """
    A call's recording in the archive: the call (its conversation and when
    it started), what the archive holds of it (`status`), its file under
    recordings/ with its audio type and length (when included), and the
    API path that downloads it from the platform while the account is open
    (`download_path`, always given).
    """

    call_id: CallId
    conversation_id: ConversationId | None = None
    started_at: Microseconds
    status: ArchivedRecordingStatus
    file: ArchivedRecordingFile | None = None
    media_type: RecordingMediaType | None = None
    total_bytes: RecordingByteCount | None = None
    download_path: CallRecordingDownloadPath
