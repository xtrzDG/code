"""Owner cabinet: playing back the recording of a phone call (concept section 8)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.booleans import StartsRecordingPlayback
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.prefixed_id import CallId
from app.schemas.typings.users.prefixed_id import UserId


class CallRecordingQuery(ImmutableDTO):
    """
    An owner or staff member plays the recording of one call of the business;
    each playback is written to the audit log. A player asks for parts of
    the file while it plays and seeks: only a read from its beginning
    (`starts_playback`) starts a playback.
    """

    user_id: UserId
    business_id: BusinessId
    call_id: CallId
    client_ip_address: ClientIpAddress | None = None
    starts_playback: StartsRecordingPlayback = True


class RecordingAudio(ImmutableDTO):
    """The audio of a call recording as stored, with its media type."""

    content: bytes = Field(repr=False)
    media_type: RecordingMediaType
