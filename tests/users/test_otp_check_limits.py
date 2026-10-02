"""How often login codes may be checked: per client network and per challenge."""

import pytest

from app.schemas.dto.users import VerifyOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.use_cases.users.otp_login.login_check_limits import CHECKS_PER_CHALLENGE
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

WRONG_CODE: OtpCode = OtpCode("000000")


def check(
    testbed: AccountsTestbed,
    challenge_id: OtpChallengeId,
    client_ip_address: str | None,
    code: OtpCode = WRONG_CODE,
) -> None:
    testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=challenge_id,
            code=code,
            client_ip_address=(
                None
                if client_ip_address is None
                else ClientIpAddress(client_ip_address)
            ),
        )
    )


def test_one_address_may_check_twenty_codes_in_ten_minutes() -> None:
    testbed = build_accounts_testbed()
    for _ in range(20):
        with pytest.raises(AuthenticationRequiredError):
            check(testbed, OtpChallengeId(), "198.51.100.7")

    with pytest.raises(RateLimitedError) as refusal:
        check(testbed, OtpChallengeId(), "198.51.100.7")

    assert refusal.value.retry_after_seconds is not None
    assert 1 <= int(refusal.value.retry_after_seconds) <= 600
    # Another address is not affected, and the window slides.
    with pytest.raises(AuthenticationRequiredError):
        check(testbed, OtpChallengeId(), "198.51.100.8")
    testbed.clock.advance(601)
    with pytest.raises(AuthenticationRequiredError):
        check(testbed, OtpChallengeId(), "198.51.100.7")


def test_the_address_limit_is_a_setting_and_counts_an_ipv6_network() -> None:
    testbed = build_accounts_testbed({"OTP_VERIFIES_PER_IP_PER_10_MINUTES": "2"})
    with pytest.raises(AuthenticationRequiredError):
        check(testbed, OtpChallengeId(), "2001:db8:1:2::10")
    with pytest.raises(AuthenticationRequiredError):
        check(testbed, OtpChallengeId(), "2001:db8:1:2::20")

    # The same /64: rotating addresses of one host share the limit.
    with pytest.raises(RateLimitedError):
        check(testbed, OtpChallengeId(), "2001:db8:1:2:ffff::1")


def test_one_challenge_takes_a_limited_number_of_checks_from_any_address() -> None:
    testbed = build_accounts_testbed({"OTP_MAX_FAILED_ATTEMPTS": "100"})
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()
    wrong_code = OtpCode("000000" if correct_code != "000000" else "111111")
    for index in range(CHECKS_PER_CHALLENGE):
        with pytest.raises(AuthenticationRequiredError):
            check(testbed, challenge.challenge_id, f"203.0.113.{index}", wrong_code)

    with pytest.raises(RateLimitedError):
        check(testbed, challenge.challenge_id, "203.0.113.200", correct_code)


def test_checks_without_a_known_address_are_limited_per_challenge_only() -> None:
    testbed = build_accounts_testbed()
    for _ in range(25):
        with pytest.raises(AuthenticationRequiredError):
            check(testbed, OtpChallengeId(), None)


def test_a_refused_check_answers_429_with_retry_after() -> None:
    testbed = build_accounts_testbed({"OTP_VERIFIES_PER_IP_PER_10_MINUTES": "1"})
    client = testbed.build_http_client()
    body = {"challenge_id": str(OtpChallengeId()), "code": "123456"}

    first = client.post("/v1/auth/otp/verify", json=body)
    second = client.post("/v1/auth/otp/verify", json=body)

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.json()["error"] == "rate_limited"
    assert 1 <= int(second.headers["Retry-After"]) <= 600
