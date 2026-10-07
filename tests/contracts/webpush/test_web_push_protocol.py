"""
Web Push as staff device notifications use it: what the platform posts to
each browser's push service (Google, Mozilla, Apple, Microsoft) follows
RFC 8030, 8291 and 8292 - the headers with none a push service does not
know, a VAPID token for that service's origin that its key verifies, and
an aes128gcm record a push service accepts; the documented answers of the
push services become the errors the delivery flow relies on.
"""

import json
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from app.clients.webpush.push_encryption import decode_base64url, load_public_key
from app.schemas.constants.notifications import WebPushUrgency
from app.schemas.exceptions.application_errors import ProviderRateLimitedError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.notifications.constrained_strings import PushEndpointUrl
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound
from tests.notifications.test_web_push_client import build_client, message
from tests.notifications.test_web_push_encryption import SENDER_PUBLIC

SPEC: str = "web_push_protocol.json"
# The client's clock in build_client.
NOW: int = 1_790_000_000
# What the HTTP stack adds to every request; the rest is Web Push.
TRANSPORT_HEADERS: frozenset[str] = frozenset(
    {"host", "accept", "accept-encoding", "connection", "user-agent", "content-length"}
)
# RFC 8292, section 2: no token valid for more than 24 hours.
MAX_TOKEN_LIFETIME_SECONDS: int = 24 * 60 * 60
# RFC 8291, section 4: a push service need not take more than 4096 octets.
MAX_BODY_BYTES: int = 4096
REQUIRED: tuple[str, ...] = ("authorization", "content-encoding", "ttl")
SALT_BYTES: int = 16
UNCOMPRESSED_POINT_BYTES: int = 65
ENDPOINTS: list[dict[str, str]] = load_json_fixture(
    "webpush", "subscription_endpoints.json"
)["endpoints"]


def posted(endpoint: str, urgency: WebPushUrgency) -> httpx.Headers:
    transport = RecordingTransport()
    transport.respond("POST", r".", None, 201)
    sent = message().model_copy(
        update={"endpoint": PushEndpointUrl(endpoint), "urgency": urgency}
    )

    build_client(transport.build()).send(sent)

    [request] = transport.requests
    assert_aes128gcm_record(request.body)
    return request.headers


def assert_aes128gcm_record(body: bytes) -> None:
    """RFC 8188, section 2.1 header as RFC 8291, section 4 fixes it."""

    record_size: int = int.from_bytes(body[SALT_BYTES : SALT_BYTES + 4], "big")
    key_id_length: int = body[SALT_BYTES + 4]
    key_id: bytes = body[SALT_BYTES + 5 : SALT_BYTES + 5 + key_id_length]
    ciphertext: bytes = body[SALT_BYTES + 5 + key_id_length :]
    assert len(body) <= MAX_BODY_BYTES
    assert key_id_length == UNCOMPRESSED_POINT_BYTES
    assert key_id[0] == 0x04
    # One record: the 16-byte tag and the padding delimiter at least.
    assert record_size >= 18
    assert 17 <= len(ciphertext) <= record_size


def token_parts(authorization: str) -> tuple[str, str]:
    token_part, key_part = authorization.removeprefix("vapid ").split(", ")
    return token_part.removeprefix("t="), key_part.removeprefix("k=")


def decoded(segment: str) -> Any:
    return json.loads(decode_base64url(segment))


def assert_signed_by(token: str, encoded_key: str) -> None:
    header, claims, signature = token.split(".")
    raw_signature: bytes = decode_base64url(signature)
    assert len(raw_signature) == 64
    public_key = load_public_key(decode_base64url(encoded_key))
    public_key.verify(
        encode_dss_signature(
            int.from_bytes(raw_signature[:32], "big"),
            int.from_bytes(raw_signature[32:], "big"),
        ),
        f"{header}.{claims}".encode("ascii"),
        ec.ECDSA(hashes.SHA256()),
    )


@pytest.mark.parametrize("subscription", ENDPOINTS, ids=lambda item: item["service"])
def test_posted_headers_and_token_follow_the_rfcs(
    subscription: dict[str, str],
) -> None:
    headers = posted(subscription["endpoint"], WebPushUrgency.HIGH)

    web_push: dict[str, str] = {
        name: value for name, value in headers.items() if name not in TRANSPORT_HEADERS
    }
    assert_outbound(web_push, SPEC, "request:push")
    token, key = token_parts(web_push["authorization"])
    header_segment, claims_segment, _ = token.split(".")
    assert_outbound(decoded(header_segment), SPEC, "VapidTokenHeader")
    claims: dict[str, Any] = decoded(claims_segment)
    assert_outbound(claims, SPEC, "VapidClaims")
    assert claims["aud"] == subscription["audience"]
    assert 0 < claims["exp"] - NOW <= MAX_TOKEN_LIFETIME_SECONDS
    assert key == SENDER_PUBLIC
    assert_signed_by(token, key)


@pytest.mark.parametrize("urgency", list(WebPushUrgency), ids=lambda item: item.value)
def test_every_urgency_is_one_rfc_8030_names(urgency: WebPushUrgency) -> None:
    headers = posted(ENDPOINTS[0]["endpoint"], urgency)

    assert_outbound(
        {"urgency": headers["urgency"]} | {name: headers[name] for name in REQUIRED},
        SPEC,
        "request:push",
    )


@pytest.mark.parametrize(
    "case",
    load_json_fixture("webpush", "push_service_replies.json")["cases"],
    ids=lambda case: case["id"],
)
def test_documented_answers_become_delivery_errors(case: dict[str, Any]) -> None:
    body: object = case["body"]
    if isinstance(body, dict):
        assert_inbound(body, SPEC, "response:push-error")
    content: bytes = (
        b""
        if body is None
        else (json.dumps(body) if isinstance(body, dict) else str(body)).encode()
    )
    client = build_client(
        httpx.MockTransport(
            lambda request: httpx.Response(
                case["status"], headers=case["headers"], content=content
            )
        )
    )

    if case["expected"] is None:
        client.send(message())
        return
    with pytest.raises(ApplicationError) as raised:
        client.send(message())

    assert type(raised.value).__name__ == case["expected"]
    if isinstance(raised.value, ProviderRateLimitedError):
        retry_after = raised.value.retry_after_seconds
        assert (None if retry_after is None else int(retry_after)) == case[
            "retry_after"
        ]
    # The endpoint is the device's address: errors never name it.
    assert "fcm.googleapis.com" not in str(raised.value)
