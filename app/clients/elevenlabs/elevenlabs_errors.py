"""ElevenLabs' refusals as the platform reports them."""

import httpx

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_object,
    read_text,
)


def raise_for_error(response: httpx.Response, path: str) -> None:
    """ExternalServiceError with the platform's reason for an HTTP error."""

    if response.status_code < 400:
        return

    body: JsonObject = parse_json_object(response.content) or {}
    detail: object = body.get("detail")
    detail_text: str = detail if isinstance(detail, str) else ""
    detail_object: JsonObject | None = read_object(body, "detail")
    if detail_object is not None:
        detail_text = read_text(detail_object, "message") or ""

    raise ExternalServiceError(
        f"ElevenLabs {path.split('/')[3]} request returned HTTP "
        f"{response.status_code}{': ' + detail_text if detail_text else ''}."
    )
