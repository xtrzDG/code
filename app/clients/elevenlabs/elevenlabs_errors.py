"""ElevenLabs' refusals as the platform reports them."""

import httpx

from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ProviderRateLimitedError,
    ProviderRejectedMessageError,
)
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_object,
    read_text,
)
from app.utilities.channels.retry_after import read_retry_after_seconds

RATE_LIMITED_STATUS_CODE: int = 429
REQUEST_TIMEOUT_STATUS_CODE: int = 408
SERVER_ERROR_STATUS_CODE: int = 500


def raise_for_error(response: httpx.Response, path: str) -> None:
    """
    The platform's reason for an HTTP error, typed by who is at fault: a
    429 is a pause ElevenLabs asked for (ProviderRateLimitedError), any
    other 4xx but a 408 is a refusal it answered (ProviderRejectedMessageError:
    an agent setting, a voice or a key it does not accept), and a 408 or a
    5xx is the platform failing (ExternalServiceError). Only the last kind
    counts against the provider:elevenlabs circuit.
    """

    status_code: int = response.status_code
    if status_code < 400:
        return

    message: str = (
        f"ElevenLabs {path.split('/')[3]} request returned HTTP "
        f"{status_code}{_detail_suffix(response)}."
    )
    if status_code == RATE_LIMITED_STATUS_CODE:
        raise ProviderRateLimitedError(
            message,
            retry_after_seconds=read_retry_after_seconds(
                None, response.headers.get("retry-after")
            ),
        )

    if status_code < SERVER_ERROR_STATUS_CODE and (
        status_code != REQUEST_TIMEOUT_STATUS_CODE
    ):
        raise ProviderRejectedMessageError(message)

    raise ExternalServiceError(message)


def _detail_suffix(response: httpx.Response) -> str:
    body: JsonObject = parse_json_object(response.content) or {}
    detail: object = body.get("detail")
    detail_text: str = detail if isinstance(detail, str) else ""
    detail_object: JsonObject | None = read_object(body, "detail")
    if detail_object is not None:
        detail_text = read_text(detail_object, "message") or ""

    return f": {detail_text}" if detail_text else ""
