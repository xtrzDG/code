"""One Graph API request and how its refusals map to platform errors."""

import httpx

from app.clients.meta.meta_graph_errors import build_graph_error
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.utilities.channels.json_values import JsonObject, parse_json_object


def graph_request(
    http_client: httpx.Client,
    method: str,
    path: str,
    access_token: str,
    *,
    params: dict[str, str] | None = None,
    json_body: JsonObject | None = None,
    is_lookup: bool = False,
) -> JsonObject:
    """
    The answer's JSON object. The token travels in the Authorization
    header, never in the URL, and transport errors are not chained.
    """

    try:
        response: httpx.Response = http_client.request(
            method,
            path,
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except httpx.HTTPError as transport_error:
        raise ExternalServiceError(
            f"Meta Graph API request failed: {type(transport_error).__name__}."
        ) from None

    body: JsonObject = parse_json_object(response.content) or {}
    if response.status_code < 400 and "error" not in body:
        return body

    raise build_graph_error(
        response.status_code,
        body,
        response.headers.get("Retry-After"),
        is_lookup=is_lookup,
    )
