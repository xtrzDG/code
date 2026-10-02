"""Reading Google API responses: errors without secrets, JSON objects, tokens."""

from typing import cast

import httpx

from app.schemas.dto.operations.calendar_connection import CalendarTokenGrant
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.bookings.constrained_integers import (
    CalendarTokenLifetimeSeconds,
)
from app.schemas.typings.bookings.strings import (
    CalendarAccessToken,
    CalendarRefreshToken,
)


def ensure_success(response: httpx.Response, operation: str) -> None:
    if response.status_code < 400:
        return

    reason: str = describe_google_error(response)
    raise ExternalServiceError(
        f"{operation} returned HTTP {response.status_code}{reason}."
    )


def describe_google_error(response: httpx.Response) -> str:
    """Google's error code ("invalid_grant") without any token or detail."""

    payload: dict[str, object] | None = find_json_object(response)
    if payload is None:
        return ""

    error: object = payload.get("error")
    if isinstance(error, str):
        return f" ({error})"

    if isinstance(error, dict):
        status: object = cast(dict[str, object], error).get("status")
        if isinstance(status, str):
            return f" ({status})"

    return ""


def read_json_object(response: httpx.Response, operation: str) -> dict[str, object]:
    payload: dict[str, object] | None = find_json_object(response)
    if payload is None:
        raise ExternalServiceError(f"{operation} returned an unexpected payload.")

    return payload


def find_json_object(response: httpx.Response) -> dict[str, object] | None:
    """The JSON object body (JSON object keys are always strings), if any."""

    try:
        payload: object = response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None

    return cast(dict[str, object], payload)


def parse_token_grant(payload: dict[str, object]) -> CalendarTokenGrant:
    access_token: object = payload.get("access_token")
    expires_in: object = payload.get("expires_in")
    refresh_token: object = payload.get("refresh_token")
    if not isinstance(access_token, str) or access_token == "":
        raise ExternalServiceError("Google returned no access token.")

    lifetime: int = expires_in if isinstance(expires_in, int) else 0
    return CalendarTokenGrant(
        access_token=CalendarAccessToken(access_token),
        refresh_token=(
            CalendarRefreshToken(refresh_token)
            if isinstance(refresh_token, str) and refresh_token != ""
            else None
        ),
        expires_in=CalendarTokenLifetimeSeconds(max(lifetime, 0)),
    )
