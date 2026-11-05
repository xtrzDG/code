"""
Downloading one customer file within a byte cap, for the messaging
platforms' media clients: the declared length is checked before the body
is read, and reading stops one chunk past the cap.
"""

import httpx

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import (
    MediaTooLargeError,
    MediaUnavailableError,
)

GONE_STATUS_CODES: frozenset[int] = frozenset({400, 403, 404, 410})
CLIENT_ERROR_CODES: range = range(400, 500)


def download_capped(
    http_client: httpx.Client,
    url: str,
    headers: dict[str, str],
    max_bytes: int,
    source: str,
) -> tuple[bytes, str | None]:
    """
    The body and its Content-Type. Errors never carry the URL (it may hold
    a token or a signed query).

    Raises:
        MediaTooLargeError: the file is longer than `max_bytes`.
        MediaUnavailableError: the server says the file is not there (4xx).
        ExternalServiceError: transport failure or a server error.
    """

    try:
        with http_client.stream("GET", url, headers=headers) as response:
            check_status(response.status_code, source)
            declared: str | None = response.headers.get("Content-Length")
            if (
                declared is not None
                and declared.isdigit()
                and int(declared) > max_bytes
            ):
                raise MediaTooLargeError(f"The {source} file is larger than allowed.")

            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise MediaTooLargeError(
                        f"The {source} file is larger than allowed."
                    )

            return bytes(body), response.headers.get("Content-Type")
    except httpx.HTTPError as error:
        raise ExternalServiceError(
            f"Downloading a {source} file failed: {type(error).__name__}."
        ) from None


def check_status(status_code: int, source: str) -> None:
    if status_code < 400:
        return

    if status_code in GONE_STATUS_CODES or status_code in CLIENT_ERROR_CODES:
        raise MediaUnavailableError(
            f"{source} does not hand out the file (HTTP {status_code})."
        )

    raise ExternalServiceError(f"{source} failed to serve a file (HTTP {status_code}).")
