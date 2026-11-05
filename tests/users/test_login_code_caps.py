"""
SMS-pumping controls: high-cost numbers, the per-country cap of codes to
new phones, the separate budget of verified users, and the alerts.
"""

import pytest

from app.schemas.constants.users import LoginCodeCap
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.exceptions.application_errors import (
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.constrained_integers import OtpSendLimit
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

RESEND_WAIT_SECONDS: int = 31


def georgian_number(index: int) -> str:
    return f"+995 555 12 34 {index:02d}"


def sign_in_owners(testbed: AccountsTestbed, count: int) -> None:
    """`count` Georgian owners sign in once (their phones become verified)."""

    for index in range(count):
        testbed.sign_in_with_phone(georgian_number(50 + index))


@pytest.mark.parametrize(
    "premium_number",
    [
        "+49 900 1234567",  # German premium rate (0900).
        "+49 180 12345",  # German shared cost (0180).
        "+49 700 12345678",  # German personal number (0700).
        "+1 900 234 5678",  # US premium rate (1-900).
    ],
)
def test_high_cost_numbers_never_get_a_code(premium_number: str) -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(ValidationFailedError, match="cannot receive login codes"):
        testbed.request_phone_code(premium_number)

    assert testbed.otp_delivery.deliveries == []


def test_denied_prefixes_come_from_the_settings() -> None:
    testbed = build_accounts_testbed({"OTP_DENIED_PHONE_PREFIXES": "+99555512, +4917"})

    with pytest.raises(ValidationFailedError):
        testbed.request_phone_code(GEORGIA_MOBILE)

    testbed.request_phone_code(GERMANY_MOBILE)
    assert len(testbed.otp_delivery.deliveries) == 1


def test_new_phones_of_one_country_are_capped_and_the_team_is_alerted() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_COUNTRY_PER_HOUR": "2"})
    testbed.request_phone_code(georgian_number(1))
    testbed.request_phone_code(georgian_number(2))

    with pytest.raises(RateLimitedError):
        testbed.request_phone_code(georgian_number(3))

    # Other countries keep working.
    testbed.request_phone_code(GERMANY_MOBILE)
    assert len(testbed.otp_delivery.deliveries) == 3
    assert testbed.cap_alerts.alerts == [
        LoginCodeCapAlert(
            cap=LoginCodeCap.COUNTRY,
            limit=OtpSendLimit(2),
            country_code=CountryCode("GE"),
        )
    ]


def test_verified_owners_are_not_held_by_the_country_cap() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_COUNTRY_PER_HOUR": "2"})
    sign_in_owners(testbed, 2)

    with pytest.raises(RateLimitedError):
        testbed.request_phone_code(georgian_number(3))

    testbed.clock.advance(RESEND_WAIT_SECONDS)
    testbed.request_phone_code(georgian_number(50))
    assert len(testbed.otp_delivery.deliveries) == 3


def test_a_flood_of_new_numbers_cannot_lock_returning_owners_out() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_HOUR": "3"})
    sign_in_owners(testbed, 1)
    testbed.request_phone_code(georgian_number(1))
    testbed.request_phone_code(georgian_number(2))

    with pytest.raises(RateLimitedError):
        testbed.request_phone_code(georgian_number(3))

    testbed.clock.advance(RESEND_WAIT_SECONDS)
    testbed.request_phone_code(georgian_number(50))
    assert [alert.cap for alert in testbed.cap_alerts.alerts] == [
        LoginCodeCap.NEW_DESTINATIONS
    ]
    stored = testbed.otp_challenge_repo.list_created_since(
        testbed.clock.microseconds_ago(3600)
    )
    assert [challenge.is_verified_destination for challenge in stored] == [
        False,
        False,
        False,
        True,
    ]


def test_verified_users_have_a_cap_of_their_own() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR": "1"})
    sign_in_owners(testbed, 2)
    testbed.clock.advance(RESEND_WAIT_SECONDS)
    testbed.request_phone_code(georgian_number(50))

    with pytest.raises(RateLimitedError):
        testbed.request_phone_code(georgian_number(51))

    testbed.request_phone_code(georgian_number(1))
    assert [alert.cap for alert in testbed.cap_alerts.alerts] == [
        LoginCodeCap.VERIFIED_USERS
    ]


def test_a_cap_refusal_answers_429() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_COUNTRY_PER_HOUR": "1"})
    client = testbed.build_http_client()
    client.post("/v1/auth/otp/start", json={"phone_number": georgian_number(1)})

    refused = client.post(
        "/v1/auth/otp/start", json={"phone_number": georgian_number(2)}
    )

    assert refused.status_code == 429
    assert refused.json()["error"] == "rate_limited"
