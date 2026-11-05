"""
The Turnstile siteverify client (scripted HTTP) and the bot check
facilitator on top of it: request shape, verdicts, failing closed.
"""

import httpx
import pytest

from app.clients.turnstile.turnstile_verification_client import (
    TurnstileVerificationClient,
)
from app.facilitators.users.turnstile_bot_check_facilitator import (
    TurnstileBotCheckFacilitator,
)
from app.schemas.dto.login_protection import TurnstileVerification
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.users.constrained_strings import (
    TurnstileAction,
    TurnstileResponseToken,
)
from app.schemas.typings.users.strings import TurnstileErrorCode
from tests.users.login_code_http import ScriptedProvider, json_response
from tests.users.login_protection_fakes import TEST_SITE_KEY

SECRET = PlatformSecret("0x4AAAA-turnstile-secret")
TOKEN = TurnstileResponseToken("0.token-from-the-widget")
ADDRESS = ClientIpAddress("198.51.100.7")


def build_client(provider: ScriptedProvider) -> TurnstileVerificationClient:
    return TurnstileVerificationClient(
        secret_key=SECRET, transport=provider.transport()
    )


def test_the_client_posts_the_token_secret_and_address_as_a_form() -> None:
    provider = ScriptedProvider(
        json_response(200, {"success": True, "action": "login", "error-codes": []})
    )

    verification = build_client(provider).verify(TOKEN, ADDRESS)

    assert verification == TurnstileVerification(
        is_passed=True, action=TurnstileAction("login")
    )
    assert provider.last.url.path == "/turnstile/v0/siteverify"
    assert provider.form_body() == {
        "secret": [str(SECRET)],
        "response": [str(TOKEN)],
        "remoteip": [str(ADDRESS)],
    }


def test_the_client_keeps_only_well_formed_error_codes_and_actions() -> None:
    provider = ScriptedProvider(
        json_response(
            200,
            {
                "success": False,
                "action": "<script>",
                "error-codes": ["timeout-or-duplicate", "Bad Code!", 7],
            },
        )
    )

    verification = build_client(provider).verify(TOKEN, None)

    assert verification == TurnstileVerification(
        is_passed=False,
        error_codes=[TurnstileErrorCode("timeout-or-duplicate")],
    )
    assert "remoteip" not in provider.form_body()


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(500, text="upstream error"),
        httpx.Response(200, text="not json"),
        httpx.ConnectTimeout("timed out"),
    ],
)
def test_the_client_reports_an_unreachable_cloudflare_without_secrets(
    answer: httpx.Response | Exception,
) -> None:
    with pytest.raises(ExternalServiceError) as failure:
        build_client(ScriptedProvider(answer)).verify(TOKEN, ADDRESS)

    assert str(SECRET) not in str(failure.value)
    assert str(TOKEN) not in str(failure.value)


class FakeVerificationClient:
    def __init__(self, answer: TurnstileVerification | Exception) -> None:
        self.answer: TurnstileVerification | Exception = answer

    def verify(
        self,
        token: TurnstileResponseToken,
        client_ip_address: ClientIpAddress | None,
    ) -> TurnstileVerification:
        del token, client_ip_address
        if isinstance(self.answer, Exception):
            raise self.answer

        return self.answer


def test_the_check_is_off_without_a_client() -> None:
    bot_check = TurnstileBotCheckFacilitator(None, TEST_SITE_KEY)

    assert bot_check.site_key() is None
    assert not bot_check.is_passed(TOKEN, ADDRESS)


@pytest.mark.parametrize(
    ("answer", "is_passed"),
    [
        (TurnstileVerification(is_passed=True, action=TurnstileAction("login")), True),
        (TurnstileVerification(is_passed=True), True),
        (TurnstileVerification(is_passed=True, action=TurnstileAction("other")), False),
        (TurnstileVerification(is_passed=False), False),
        (ExternalServiceError("Turnstile siteverify returned HTTP 500."), False),
    ],
)
def test_the_check_passes_only_a_valid_token_of_the_login_form(
    answer: TurnstileVerification | Exception,
    is_passed: bool,
) -> None:
    bot_check = TurnstileBotCheckFacilitator(
        FakeVerificationClient(answer), TEST_SITE_KEY
    )

    assert bot_check.site_key() == TEST_SITE_KEY
    assert bot_check.is_passed(TOKEN, ADDRESS) is is_passed
