import httpx
from typed_time_provider import Microseconds

from app.clients.meta.meta_graph_client import (
    DEFAULT_GRAPH_API_VERSION,
    META_GRAPH_BASE_URL,
    REQUEST_TIMEOUT_SECONDS,
)
from app.clients.meta.meta_graph_errors import build_graph_error
from app.contracts.channel_clients import ProviderToken
from app.contracts.channel_credentials import MetaTokenDebugClientContract
from app.schemas.dto.channels.credential_inspection import MetaTokenFacts
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from app.utilities.channels.json_values import (
    JsonObject,
    parse_json_object,
    read_flag,
    read_integer,
    read_object,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


class MetaTokenDebugClient(MetaTokenDebugClientContract):
    """
    Graph API `GET /debug_token`: whether a page or system user token still
    works and when it, or its data access, runs out. The app's own token
    (`{app_id}|{app_secret}`) travels in the Authorization header; the
    inspected token is the `input_token` parameter Meta requires (httpx's
    request log is muted, and errors never carry the URL).
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        api_version: str = DEFAULT_GRAPH_API_VERSION,
        base_url: str = META_GRAPH_BASE_URL,
    ) -> None:
        self._http_client: httpx.Client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/{api_version}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def inspect_token(
        self,
        token: ProviderToken,
        app_id: PlatformIdentifier,
        app_secret: PlatformSecret,
    ) -> MetaTokenFacts:
        try:
            response: httpx.Response = self._http_client.get(
                "/debug_token",
                params={"input_token": str(token)},
                headers={"Authorization": f"Bearer {app_id}|{app_secret}"},
            )
        except httpx.HTTPError as transport_error:
            raise ExternalServiceError(
                f"Meta debug_token failed: {type(transport_error).__name__}."
            ) from None

        body: JsonObject = parse_json_object(response.content) or {}
        if response.status_code >= 400 or "error" in body:
            raise build_graph_error(
                response.status_code,
                body,
                response.headers.get("Retry-After"),
                is_lookup=True,
            )

        data: JsonObject = read_object(body, "data") or {}
        return MetaTokenFacts(
            is_valid=read_flag(data, "is_valid"),
            expires_at=earliest_end(
                read_integer(data, "expires_at"),
                read_integer(data, "data_access_expires_at"),
            ),
        )


def earliest_end(*unix_seconds: int | None) -> Microseconds | None:
    """The earliest of Meta's end times in seconds (0 or missing: no end)."""

    ends: list[int] = [seconds for seconds in unix_seconds if seconds]
    return Microseconds(min(ends) * MICROSECONDS_PER_SECOND) if ends else None
