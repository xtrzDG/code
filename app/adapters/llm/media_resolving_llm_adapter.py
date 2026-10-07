import base64
import json
import logging
from collections.abc import Sequence

from app.adapters.llm.llm_payloads import STORED_MEDIA_SOURCE
from app.contracts.llm import LlmAdapterContract
from app.contracts.media_storage import MediaStorageAdapterContract
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput, MediaLocation, StoredMediaFile
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.media.strings import MediaStoragePath
from app.utilities.conversations.llm_transcript import (
    USER_ROLE,
    parse_transcript_turn,
    read_object_list,
    read_string,
)

logger: logging.Logger = logging.getLogger(__name__)
# Pictures sent again with every request of a conversation: the newest few
# are enough to talk about, and each costs tokens every time.
MAX_REPLAYED_PHOTOS: int = 4
EARLIER_PHOTO_NOTE: str = "[Photo sent earlier in the conversation]"
GONE_PHOTO_NOTE: str = "[Photo: it is no longer available]"


class MediaResolvingLlmAdapter(LlmAdapterContract):
    """
    Shows the model the photos customers sent. User turns keep references
    to the stored photos; before each request the newest photos of the
    transcript (MAX_REPLAYED_PHOTOS) are read from the business's media
    storage and sent as pictures, older ones as a short note, and one the
    retention purge or an erasure removed as "no longer available". The
    stored transcript never holds a picture's bytes.
    """

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        media_storage: MediaStorageAdapterContract,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._media_storage: MediaStorageAdapterContract = media_storage

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._inner_adapter.build_user_text_turn(text)

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_user_media_turn(text, images)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        """
        The photos of the transcript, and of the provider-neutral one a
        fallback model would be sent, resolved before the call.
        """

        update: dict[str, object] = {}
        if has_stored_media(request.transcript):
            update["transcript"] = self._resolve(request.transcript)

        if request.fallback_transcript is not None and has_stored_media(
            request.fallback_transcript
        ):
            update["fallback_transcript"] = self._resolve(request.fallback_transcript)

        if not update:
            return self._inner_adapter.complete(request)

        return self._inner_adapter.complete(request.model_copy(update=update))

    def _resolve(
        self, transcript: list[LlmProviderPayload]
    ) -> list[LlmProviderPayload]:
        remaining: int = MAX_REPLAYED_PHOTOS
        resolved: list[LlmProviderPayload] = []
        for payload in reversed(transcript):
            turn: dict[str, object] = parse_transcript_turn(payload)
            blocks: list[dict[str, object]] = read_object_list(turn.get("content"))
            if turn.get("role") != USER_ROLE or not any(
                is_stored_photo(b) for b in blocks
            ):
                resolved.append(payload)
                continue

            content: list[dict[str, object]] = []
            for block in blocks:
                if not is_stored_photo(block):
                    content.append(block)
                elif remaining <= 0:
                    content.append(note(EARLIER_PHOTO_NOTE))
                else:
                    remaining -= 1
                    content.append(self._picture(block))

            resolved.append(
                LlmProviderPayload(
                    json.dumps({**turn, "content": content}, ensure_ascii=False)
                )
            )

        return list(reversed(resolved))

    def _picture(self, block: dict[str, object]) -> dict[str, object]:
        source: dict[str, object] = read_source(block)
        business_id: str | None = read_string(source, "business_id")
        path: str | None = read_string(source, "path")
        if business_id is None or path is None:
            return note(GONE_PHOTO_NOTE)

        try:
            photo: StoredMediaFile | None = self._media_storage.read(
                MediaLocation(
                    business_id=BusinessId(business_id), path=MediaStoragePath(path)
                )
            )
        except ExternalServiceError, ValueError:
            logger.exception("A stored photo could not be read for the model.")
            photo = None

        if photo is None:
            return note(GONE_PHOTO_NOTE)

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": str(photo.media_type),
                "data": base64.b64encode(photo.content).decode("ascii"),
            },
        }


def has_stored_media(transcript: list[LlmProviderPayload]) -> bool:
    return any(STORED_MEDIA_SOURCE in str(payload) for payload in transcript)


def is_stored_photo(block: dict[str, object]) -> bool:
    return (
        read_string(block, "type") == "image"
        and read_string(read_source(block), "type") == STORED_MEDIA_SOURCE
    )


def read_source(block: dict[str, object]) -> dict[str, object]:
    sources: list[dict[str, object]] = read_object_list([block.get("source")])
    return sources[0] if sources else {}


def note(text: str) -> dict[str, object]:
    return {"type": "text", "text": text}
