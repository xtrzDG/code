"""The `ErrorBody` answers middleware sends before any route runs."""

from collections.abc import Mapping

from starlette.types import Scope, Send

from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.errors import ErrorBody
from app.schemas.typings.platform.strings import ErrorMessageText


async def send_error_answer(
    send: Send,
    status: int,
    code: ApiErrorCode,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> None:
    """One JSON `ErrorBody` answer with its status and extra headers."""

    body: bytes = (
        ErrorBody(error=code, message=ErrorMessageText(message))
        .model_dump_json(exclude_none=True)
        .encode("utf-8")
    )
    raw_headers: list[tuple[bytes, bytes]] = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("latin-1")),
    ]
    raw_headers.extend(
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    )
    await send(
        {"type": "http.response.start", "status": status, "headers": raw_headers}
    )
    await send({"type": "http.response.body", "body": body})


def client_address_of(scope: Scope) -> str | None:
    """The caller's address as the server sees it (after trusted proxies)."""

    client: object = scope.get("client")
    if isinstance(client, tuple) and client and isinstance(client[0], str):
        return client[0]

    return None


def header_map(scope: Scope) -> dict[str, str]:
    """The request's headers by lower-case name (the first of repeats)."""

    headers: dict[str, str] = {}
    for name, value in scope.get("headers", []):
        headers.setdefault(name.decode("latin-1").lower(), value.decode("latin-1"))

    return headers
