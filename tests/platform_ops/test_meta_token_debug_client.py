"""
Graph API `debug_token` as the token check asks it: the app token in the
Authorization header, the inspected token as `input_token`, the earlier
of the token's and its data access's end, and Meta's refusals as errors.
"""

import json

import httpx
import pytest
from typed_time_provider import Microseconds

from app.clients.meta.meta_token_debug_client import MetaTokenDebugClient, earliest_end
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

TOKEN: ChannelSecret = ChannelSecret("test-token-0000")
APP_ID: PlatformIdentifier = PlatformIdentifier("1234567890")
APP_SECRET: PlatformSecret = PlatformSecret("test-app-secret-0000")  # gitleaks:allow


def client_answering(
    status_code: int, body: object, requests: list[httpx.Request]
) -> MetaTokenDebugClient:
    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, content=json.dumps(body).encode())

    return MetaTokenDebugClient(transport=httpx.MockTransport(answer))


def test_the_token_is_asked_about_with_the_app_token() -> None:
    requests: list[httpx.Request] = []
    client = client_answering(
        200,
        {
            "data": {
                "is_valid": True,
                "type": "PAGE",
                "expires_at": 1_790_000_000,
                "data_access_expires_at": 1_795_000_000,
            }
        },
        requests,
    )

    facts = client.inspect_token(TOKEN, APP_ID, APP_SECRET)

    assert facts.is_valid is True
    assert facts.expires_at == Microseconds(1_790_000_000_000_000)
    [request] = requests
    assert request.url.path == "/v23.0/debug_token"
    assert request.url.params["input_token"] == str(TOKEN)
    assert request.headers["Authorization"] == f"Bearer {APP_ID}|{APP_SECRET}"


def test_a_system_user_token_never_runs_out() -> None:
    client = client_answering(
        200,
        {"data": {"is_valid": True, "expires_at": 0, "data_access_expires_at": 0}},
        [],
    )

    assert client.inspect_token(TOKEN, APP_ID, APP_SECRET).expires_at is None


def test_a_revoked_token_reads_as_invalid() -> None:
    client = client_answering(200, {"data": {"is_valid": False, "expires_at": 0}}, [])

    facts = client.inspect_token(TOKEN, APP_ID, APP_SECRET)

    assert facts.is_valid is False and facts.expires_at is None


def test_meta_refusing_the_app_is_an_error() -> None:
    client = client_answering(
        400,
        {"error": {"message": "Invalid OAuth access token.", "code": 190}},
        [],
    )

    with pytest.raises(ApplicationError):
        client.inspect_token(TOKEN, APP_ID, APP_SECRET)


def test_meta_out_of_reach_is_an_external_failure() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable", request=request)

    client = MetaTokenDebugClient(transport=httpx.MockTransport(fail))

    with pytest.raises(ExternalServiceError, match="ConnectError"):
        client.inspect_token(TOKEN, APP_ID, APP_SECRET)


def test_the_earliest_end_ignores_ends_meta_does_not_set() -> None:
    assert earliest_end(None, 0) is None
    assert earliest_end(20, None, 10) == Microseconds(10_000_000)
