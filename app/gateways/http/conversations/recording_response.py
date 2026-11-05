"""
The HTTP answer with a call recording: the whole audio, or the byte range a
media player asked for.
"""

from fastapi import Response
from fastapi.responses import JSONResponse

from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.call_recordings import RecordingByteRange, RecordingPart
from app.schemas.dto.errors import ErrorBody
from app.schemas.typings.platform.strings import ErrorMessageText

# A recording is personal data: no HTTP cache keeps it (shared proxies and
# CDNs least of all); the browser's player buffers it in memory and asks for
# parts of it (byte ranges) while it plays and seeks.
RECORDING_RESPONSE_HEADERS: dict[str, str] = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
}
RANGE_OUTSIDE_RECORDING: str = "The requested range lies outside the recording."
RECORDING_OPENAPI_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "The call recording (audio/mpeg from the voice platform).",
        "content": {"audio/*": {"schema": {"type": "string", "format": "binary"}}},
    },
    206: {
        "description": "The part of the recording a `Range: bytes=…` header asks "
        "for (media players ask for parts while they play and seek).",
        "content": {"audio/*": {"schema": {"type": "string", "format": "binary"}}},
    },
    416: {"model": ErrorBody, "description": RANGE_OUTSIDE_RECORDING},
}


def build_recording_response(
    part: RecordingPart,
    requested_range: RecordingByteRange | None,
) -> Response:
    """
    The whole recording, or the part a media player asked for (206; an
    open range may be answered with its first megabytes, the player asks
    for the rest), or 416 for a range outside it. Every answer says ranges
    are served: Safari and iOS play only media that supports them, and
    other browsers can then seek.
    """

    total_length: int = int(part.total_bytes)
    headers: dict[str, str] = {**RECORDING_RESPONSE_HEADERS, "Accept-Ranges": "bytes"}
    if requested_range is None:
        return Response(
            content=part.content,
            media_type=str(part.media_type),
            headers=headers,
        )

    if not part.content:
        return JSONResponse(
            status_code=416,
            content=ErrorBody(
                error=ApiErrorCode.VALIDATION_FAILED,
                message=ErrorMessageText(RANGE_OUTSIDE_RECORDING),
            ).model_dump(mode="json", exclude_none=True),
            headers={**headers, "Content-Range": f"bytes */{total_length}"},
        )

    first_byte: int = int(part.first_byte)
    last_byte: int = first_byte + len(part.content) - 1
    return Response(
        content=part.content,
        status_code=206,
        media_type=str(part.media_type),
        headers={
            **headers,
            "Content-Range": f"bytes {first_byte}-{last_byte}/{total_length}",
        },
    )
