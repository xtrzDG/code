"""Owner cabinet: playing back the recording of a phone call (concept section 8)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import StartsRecordingPlayback
from app.schemas.typings.conversations.constrained_integers import (
    RecordingByteCount,
    RecordingByteOffset,
)
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.conversations.strings import RecordingStoragePath
from app.schemas.typings.users.prefixed_id import UserId


class RecordingByteRange(ImmutableDTO):
    """
    The one part of a recording a media player asks for (an HTTP `Range`):
    `first_byte`-`last_byte` (both inclusive, the last one open when None),
    or the final `suffix_length` bytes.
    """

    first_byte: RecordingByteOffset | None = None
    last_byte: RecordingByteOffset | None = None
    suffix_length: RecordingByteCount | None = None


class CallRecordingQuery(ImmutableDTO):
    """
    An owner or staff member plays the recording of one call of the business;
    each playback is written to the audit log. A player asks for parts of
    the file while it plays and seeks (`byte_range`): only a read from its
    beginning (`starts_playback`) starts a playback.
    """

    user_id: UserId
    business_id: BusinessId
    call_id: CallId
    client_ip_address: ClientIpAddress | None = None
    starts_playback: StartsRecordingPlayback = True
    byte_range: RecordingByteRange | None = None


class RecordingLocation(ImmutableDTO):
    """
    Where a recording is kept: its path in the recording storage and the
    business it belongs to (the business's own key encrypts it).
    """

    business_id: BusinessId
    path: RecordingStoragePath


class CallRecordingMove(ImmutableDTO):
    """A call's recording archived from `from_path` to `to_path`."""

    from_path: RecordingStoragePath
    to_path: RecordingStoragePath
    moved_at: Microseconds


class CallRecordingArchiveJobPayload(ImmutableDTO):
    """Payload of the queued job that archives one call's recording."""

    call_id: CallId


class RecordingAudio(ImmutableDTO):
    """The audio of a call recording as stored, with its media type."""

    content: bytes = Field(repr=False)
    media_type: RecordingMediaType


class RecordingPart(ImmutableDTO):
    """
    The part of a recording a read asked for: `content` starts at
    `first_byte` of a recording `total_bytes` long (the whole recording
    when no range was asked for; empty when the range lies outside it).
    """

    content: bytes = Field(repr=False)
    media_type: RecordingMediaType
    first_byte: RecordingByteOffset
    total_bytes: RecordingByteCount
