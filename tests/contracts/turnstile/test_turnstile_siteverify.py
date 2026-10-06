"""
Cloudflare Turnstile siteverify as the login uses it: the form the
platform posts matches the documented request with no field Cloudflare
does not know, and the documented answers (passed, an invalid token, a
token used twice) match the documented shape and are read.
"""

from typing import Any
from urllib.parse import parse_qsl

import pytest

from app.clients.turnstile.turnstile_verification_client import (
    TurnstileVerificationClient,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import TurnstileResponseToken
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

SPEC: str = "turnstile_siteverify.json"
# Cloudflare's documented testing secret and dummy token.
TEST_SECRET = PlatformSecret("1x0000000000000000000000000000000AA")
DUMMY_TOKEN = TurnstileResponseToken("XXXX.DUMMY.TOKEN.XXXX")


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("siteverify_success.json", (True, "login", [])),
        ("siteverify_invalid_token.json", (False, None, ["invalid-input-response"])),
        ("siteverify_duplicate.json", (False, None, ["timeout-or-duplicate"])),
    ],
)
def test_documented_answers_match_and_are_read(
    fixture: str, expected: tuple[bool, str | None, list[str]]
) -> None:
    answer: dict[str, Any] = load_json_fixture("turnstile", fixture)
    assert_inbound(answer, SPEC, "response:siteverify")
    transport = RecordingTransport()
    transport.respond("POST", r"/turnstile/v0/siteverify$", answer)
    client = TurnstileVerificationClient(TEST_SECRET, transport=transport.build())

    verification = client.verify(DUMMY_TOKEN, ClientIpAddress("203.0.113.7"))

    assert (
        verification.is_passed,
        None if verification.action is None else str(verification.action),
        [str(code) for code in verification.error_codes],
    ) == expected
    [request] = transport.requests
    form: dict[str, str] = dict(parse_qsl(request.body.decode()))
    assert_outbound(form, SPEC, "request:siteverify")
