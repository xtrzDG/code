"""
The bot check (Cloudflare Turnstile, faked) of risky login code requests:
needed only on a risk signal, and only when the check is on. No signal
depends on whether the phone or e-mail belongs to someone: every phone is
checked (a paid text message), an e-mail only on a busy address or a busy
platform (test_login_enumeration.py compares the answers).
"""

import pytest

from app.schemas.dto.users import StartOtpLoginCommand
from app.schemas.exceptions.login_errors import BotCheckRequiredError
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import TurnstileResponseToken
from app.schemas.typings.users.strings import RawEmailAddressInput
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed
from tests.users.login_protection_fakes import (
    FAILING_TOKEN,
    PASSING_TOKEN,
    TEST_SITE_KEY,
)

RESEND_WAIT_SECONDS: int = 31


def request_code(
    testbed: AccountsTestbed,
    raw_phone_number: str = GEORGIA_MOBILE,
    token: TurnstileResponseToken | None = None,
    ip_address: str = "198.51.100.1",
) -> None:
    testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput(raw_phone_number),
            turnstile_token=token,
            client_ip_address=ClientIpAddress(ip_address),
        )
    )


OWNER_EMAIL: str = "owner@salobie.example"


def request_email_code(
    testbed: AccountsTestbed,
    email: str = OWNER_EMAIL,
    token: TurnstileResponseToken | None = None,
    ip_address: str = "198.51.100.1",
) -> None:
    testbed.start_otp_login.run(
        StartOtpLoginCommand(
            email=RawEmailAddressInput(email),
            turnstile_token=token,
            client_ip_address=ClientIpAddress(ip_address),
        )
    )


def build_with_returning_owner(
    environment_variables: dict[str, str] | None = None,
) -> AccountsTestbed:
    """
    A testbed whose Georgian owner signed in once by phone and once by
    e-mail; the check is on.
    """

    testbed = build_accounts_testbed(environment_variables)
    testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.sign_in_with_email(OWNER_EMAIL)
    testbed.clock.advance(RESEND_WAIT_SECONDS)
    testbed.bot_check.turn_on()
    return testbed


def test_with_the_check_off_no_request_needs_a_token() -> None:
    testbed = build_accounts_testbed()

    request_code(testbed)

    assert len(testbed.otp_delivery.deliveries) == 1
    assert testbed.bot_check.checked_tokens == []


def test_a_new_phone_needs_a_passed_check() -> None:
    testbed = build_accounts_testbed()
    testbed.bot_check.turn_on()

    with pytest.raises(BotCheckRequiredError) as refusal:
        request_code(testbed)

    reason = refusal.value.reasons[0]
    assert str(reason.code) == "challenge_required"
    assert [str(detail) for detail in reason.details] == [str(TEST_SITE_KEY)]
    assert testbed.otp_delivery.deliveries == []

    with pytest.raises(BotCheckRequiredError, match="not passed"):
        request_code(testbed, token=FAILING_TOKEN)

    request_code(testbed, token=PASSING_TOKEN)

    assert len(testbed.otp_delivery.deliveries) == 1
    assert testbed.bot_check.checked_addresses[-1] == ClientIpAddress("198.51.100.1")


def test_an_email_on_a_quiet_day_is_not_checked_known_or_not() -> None:
    testbed = build_with_returning_owner()

    request_email_code(testbed)
    request_email_code(testbed, "new@example.com")

    assert len(testbed.otp_delivery.deliveries) == 4
    assert testbed.bot_check.checked_tokens == []


def test_every_phone_is_checked_a_returning_owners_too() -> None:
    testbed = build_with_returning_owner()

    with pytest.raises(BotCheckRequiredError):
        request_code(testbed)
    request_code(testbed, token=PASSING_TOKEN)

    assert len(testbed.otp_delivery.deliveries) == 3
    assert testbed.bot_check.checked_tokens == [PASSING_TOKEN]


def test_a_busy_client_address_is_checked_even_for_a_returning_owner() -> None:
    testbed = build_with_returning_owner()
    for index in range(3):
        request_email_code(
            testbed, f"guest{index}@example.com", ip_address="198.51.100.9"
        )

    with pytest.raises(BotCheckRequiredError):
        request_email_code(testbed, ip_address="198.51.100.9")

    request_email_code(testbed, ip_address="198.51.100.1")


def test_a_high_risk_country_is_checked_even_for_a_returning_owner() -> None:
    testbed = build_with_returning_owner({"OTP_HIGH_RISK_COUNTRIES": "GE,TV"})

    with pytest.raises(BotCheckRequiredError):
        request_code(testbed)

    request_code(testbed, token=PASSING_TOKEN)


def test_half_the_platform_budget_used_checks_every_request() -> None:
    testbed = build_with_returning_owner({"OTP_SENDS_PER_HOUR": "4"})
    # The owner's two first sign-ins (new destinations then) are half the
    # budget of unknown destinations; the owner's own budget is untouched.

    with pytest.raises(BotCheckRequiredError):
        request_email_code(testbed, "new@example.com")
    # The owner's address is checked too: which budget a destination
    # counts against must not tell whether it belongs to someone.
    with pytest.raises(BotCheckRequiredError):
        request_email_code(testbed)


def test_a_refused_request_answers_403_with_the_site_key() -> None:
    testbed = build_accounts_testbed()
    testbed.bot_check.turn_on()
    client = testbed.build_http_client()

    refused = client.post("/v1/auth/otp/start", json={"phone_number": GEORGIA_MOBILE})
    passed = client.post(
        "/v1/auth/otp/start",
        json={"phone_number": GEORGIA_MOBILE, "turnstile_token": str(PASSING_TOKEN)},
    )

    assert refused.status_code == 403
    assert refused.json()["error"] == "access_denied"
    assert refused.json()["reasons"] == [
        {
            "code": "challenge_required",
            "message": "Confirm that you are not a robot, then ask for the code again.",
            "details": [str(TEST_SITE_KEY)],
        }
    ]
    assert passed.status_code == 200
