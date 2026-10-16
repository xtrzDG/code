"""Small fakes and samples of the previous-key tests."""

from collections.abc import Iterable

from typed_time_provider import Microseconds

from app.contracts.object_storage import ObjectStorageClientContract
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.dto.call_recordings import RecordingAudio, RecordingLocation
from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload
from app.schemas.dto.notifications.staff_links import StaffLinkClaims
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import TelegramWebhookSecret
from app.schemas.typings.channels.strings import WebhookSignatureHeader
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import RecordingStoragePath

BUSINESS_ID: BusinessId = BusinessId()
LINK_EXPIRES_AT: Microseconds = Microseconds(1_900_000_000_000_000)


class DictObjectStorage(ObjectStorageClientContract):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, key: RecordingStoragePath, body: bytes) -> None:
        self.objects[str(key)] = body

    def put_object_parts(
        self, key: RecordingStoragePath, parts: Iterable[bytes]
    ) -> None:
        self.objects[str(key)] = b"".join(parts)

    def get_object_range(
        self, key: RecordingStoragePath, first_byte: int, last_byte: int
    ) -> bytes | None:
        stored: bytes | None = self.objects.get(str(key))
        return None if stored is None else stored[first_byte : last_byte + 1]

    def delete_object(self, key: RecordingStoragePath) -> None:
        self.objects.pop(str(key), None)


def webhook_payload(secret: TelegramWebhookSecret) -> ChannelWebhookPayload:
    return ChannelWebhookPayload(
        body=b"{}", signature_header=WebhookSignatureHeader(str(secret))
    )


def link_claims() -> StaffLinkClaims:
    return StaffLinkClaims(
        business_id=BUSINESS_ID,
        target=StaffLinkTarget.NOTIFICATIONS,
        expires_at=LINK_EXPIRES_AT,
    )


def recording_location() -> RecordingLocation:
    return RecordingLocation(
        business_id=BUSINESS_ID,
        path=RecordingStoragePath(f"{BUSINESS_ID}/calls/call-1.mp3"),
    )


def recording() -> RecordingAudio:
    return RecordingAudio(
        content=bytes(range(256)) * 700, media_type=RecordingMediaType("audio/mpeg")
    )
