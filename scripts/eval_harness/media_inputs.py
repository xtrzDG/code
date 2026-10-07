"""
The media a scenario's first message carries (`attachment`): a voice note
the platform already transcribed (its transcript is the persona's message,
as the worker hands it to the conversation engine), or a photo from
evals/media kept in the run's media storage so the engine shows it to the
model like a photo a customer sent. The storage is in memory: an
evaluation never writes a file outside its report.
"""

import threading
from dataclasses import dataclass
from pathlib import Path

from app.contracts.media_storage import MediaStorageAdapterContract
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.message_media import MessageAttachment
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.media.constrained_integers import (
    AudioDurationSeconds,
    MediaByteCount,
)
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.strings import MediaStoragePath, TranscribedVoiceText
from scripts.eval_harness.dataset_setup_models import AttachmentSpec

VOICE_MEDIA_TYPE: MessageMediaType = MessageMediaType("audio/ogg")
PHOTO_MEDIA_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
# People say about two and a half words a second in a voice note.
WORDS_PER_SECOND: float = 2.5
PHOTO_PATH_PREFIX: str = "evals"


class InMemoryMediaStorage(MediaStorageAdapterContract):
    """The run's customer files, kept in memory (technical adapter)."""

    def __init__(self) -> None:
        self._files: dict[tuple[str, str], StoredMediaFile] = {}
        self._lock = threading.Lock()

    def store(self, location: MediaLocation, media: StoredMediaFile) -> None:
        with self._lock:
            self._files[key(location)] = media

    def read(self, location: MediaLocation) -> StoredMediaFile | None:
        with self._lock:
            return self._files.get(key(location))

    def delete(self, location: MediaLocation) -> None:
        with self._lock:
            self._files.pop(key(location), None)


def key(location: MediaLocation) -> tuple[str, str]:
    return str(location.business_id), str(location.path)


@dataclass(frozen=True)
class FirstMessageMedia:
    """Turns the persona's first message into what the channel delivered."""

    attachment: AttachmentSpec
    storage: MediaStorageAdapterContract
    business_id: BusinessId
    media_dir: Path

    def deliver(self, text: MessageText) -> tuple[MessageText, list[MessageAttachment]]:
        """The typed text (none for a voice note) and the attachments."""

        if self.attachment.voice_note:
            return MessageText(""), [voice_note(str(text))]

        return text, [self._photo()]

    def _photo(self) -> MessageAttachment:
        name: str = str(self.attachment.photo)
        content: bytes = (self.media_dir / name).read_bytes()
        media_type = MessageMediaType(PHOTO_MEDIA_TYPES[Path(name).suffix.lower()])
        path = MediaStoragePath(f"{PHOTO_PATH_PREFIX}/{name}")
        self.storage.store(
            MediaLocation(business_id=self.business_id, path=path),
            StoredMediaFile(content=content, media_type=media_type),
        )
        return MessageAttachment(
            kind=AttachmentKind.IMAGE,
            storage_path=path,
            media_type=media_type,
            byte_count=MediaByteCount(len(content)),
        )


def voice_note(transcript: str) -> MessageAttachment:
    """A voice note the worker transcribed: its words and its length."""

    seconds: int = max(1, round(len(transcript.split()) / WORDS_PER_SECOND))
    return MessageAttachment(
        kind=AttachmentKind.AUDIO,
        media_type=VOICE_MEDIA_TYPE,
        duration_seconds=AudioDurationSeconds(seconds),
        transcript=TranscribedVoiceText(transcript),
    )
