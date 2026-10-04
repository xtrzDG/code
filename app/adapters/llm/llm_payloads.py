"""Anthropic Messages API turn shapes shared by the real and scripted adapters.

Payloads are JSON objects `{"role": ..., "content": [...]}` stored verbatim
and replayed in order, so the transcript stays append-only.
"""

import json
from collections.abc import Sequence

from app.schemas.dto.conversations import LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText

STORED_MEDIA_SOURCE: str = "stored_media"


def build_user_text_payload(text: MessageText) -> LlmProviderPayload:
    return LlmProviderPayload(
        json.dumps(
            {"role": "user", "content": [{"type": "text", "text": str(text)}]},
            ensure_ascii=False,
        )
    )


def build_user_media_payload(
    text: MessageText, images: Sequence[LlmImageInput]
) -> LlmProviderPayload:
    """
    The text, then one `image` block per photo whose source names the
    stored file (`stored_media`); `media_resolving_llm_adapter` turns it
    into the picture's bytes for each request.
    """

    content: list[dict[str, object]] = [{"type": "text", "text": str(text)}]
    content.extend(
        {
            "type": "image",
            "source": {
                "type": STORED_MEDIA_SOURCE,
                "business_id": str(image.location.business_id),
                "path": str(image.location.path),
                "media_type": str(image.media_type),
            },
        }
        for image in images
    )
    return LlmProviderPayload(
        json.dumps({"role": "user", "content": content}, ensure_ascii=False)
    )


def build_tool_results_payload(results: list[LlmToolResult]) -> LlmProviderPayload:
    content: list[dict[str, object]] = []
    for result in results:
        content.append(
            {
                "type": "tool_result",
                "tool_use_id": str(result.call_id),
                "content": str(result.result_json),
                "is_error": result.is_error,
            }
        )

    return LlmProviderPayload(
        json.dumps({"role": "user", "content": content}, ensure_ascii=False)
    )
