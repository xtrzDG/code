"""
Meta's token endpoints as the platform's real MetaOAuthClient speaks them:
the renewal of a WhatsApp Embedded Signup token (the Refresh API of system
user tokens: `GET /oauth/access_token` with `grant_type=fb_exchange_token`
and `set_token_expires_in_60_days=true`) and `debug_token`'s answer for
that business token.

Meta publishes no machine-readable specification of these endpoints (the
vendored WhatsApp spec does not cover them), so the fixtures follow the
documented samples of developers.facebook.com
(/docs/business-management-apis/system-users/install-apps-and-generate-tokens,
/docs/graph-api/reference/debug_token) with low-entropy test values.
"""

from typing import Any

from typed_time_provider import Microseconds

from app.clients.meta.meta_oauth_client import MetaOAuthClient
from app.schemas.dto.channels.meta_provider import MetaAppCredentials, MetaTokenGrants
from app.schemas.typings.channels.constrained_strings import MetaObjectId
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaPermissionName,
)
from app.schemas.typings.meta_connection.strings import MetaAccessToken
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture

APP = MetaAppCredentials(
    app_id=PlatformIdentifier("1234567890"),
    app_secret=PlatformSecret("test-app-secret-0000"),
)
OLD_TOKEN = MetaAccessToken("EAAfake-token-1")
NEW_TOKEN = MetaAccessToken("EAAfake-token-2")
REFRESH_ANSWER: str = "system_user_token_refresh.json"
DEBUG_ANSWER: str = "debug_token_business_token.json"
WABA = MetaObjectId("102290129340398")
# The fixture's `expires_at`: 2027-01-19 09:00 UTC, 60 days after issue.
NEW_TOKEN_END = Microseconds(1_800_349_200 * 1_000_000)


def read_grants(answer: dict[str, Any]) -> tuple[MetaTokenGrants, RecordingTransport]:
    graph = RecordingTransport()
    graph.respond("GET", r"/debug_token$", answer)
    grants = MetaOAuthClient(transport=graph.build()).read_grants(NEW_TOKEN, APP)
    return grants, graph


def test_the_refresh_asks_meta_exactly_as_documented() -> None:
    graph = RecordingTransport()
    graph.respond(
        "GET", r"/oauth/access_token$", load_json_fixture("meta", REFRESH_ANSWER)
    )

    token = MetaOAuthClient(transport=graph.build()).refresh_business_token(
        OLD_TOKEN, APP
    )

    [request] = graph.requests
    assert token == NEW_TOKEN
    assert request.method == "GET"
    assert (request.url.scheme, request.url.host) == ("https", "graph.facebook.com")
    assert request.path == "/v23.0/oauth/access_token"
    assert sorted(request.url.params.multi_items()) == [
        ("client_id", "1234567890"),
        ("client_secret", "test-app-secret-0000"),
        ("fb_exchange_token", "EAAfake-token-1"),
        ("grant_type", "fb_exchange_token"),
        ("set_token_expires_in_60_days", "true"),
    ]
    # The app secret travels as Meta documents it; no other credential goes.
    assert "Authorization" not in request.headers
    assert "appsecret_proof" not in request.url.params
    assert request.body == b""


def test_debug_token_tells_the_business_tokens_end_and_accounts() -> None:
    grants, graph = read_grants(load_json_fixture("meta", DEBUG_ANSWER))

    [request] = graph.requests
    assert request.path == "/v23.0/debug_token"
    assert request.url.params["input_token"] == str(NEW_TOKEN)
    assert request.headers["Authorization"] == "Bearer 1234567890|test-app-secret-0000"
    assert grants.expires_at == NEW_TOKEN_END
    for permission in ("whatsapp_business_management", "whatsapp_business_messaging"):
        assert grants.targets_of(MetaPermissionName(permission)) == [WABA]


def test_a_token_without_an_end_reads_as_never_ending() -> None:
    # Meta writes 0 (or nothing) for a token that does not expire; the end
    # of the app's data access is not the token's own end.
    without_end: dict[str, Any] = load_json_fixture("meta", DEBUG_ANSWER)
    without_end["data"]["expires_at"] = 0
    without_end["data"]["data_access_expires_at"] = 1_800_349_200
    missing_end: dict[str, Any] = load_json_fixture("meta", DEBUG_ANSWER)
    del missing_end["data"]["expires_at"]

    assert read_grants(without_end)[0].expires_at is None
    assert read_grants(missing_end)[0].expires_at is None
