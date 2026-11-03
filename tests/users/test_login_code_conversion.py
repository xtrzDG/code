"""
The automatic throttle of login codes to new phones whose codes go unused
(VOICE-03): a number range is denied for the hour, a country's cap drops.
"""

import pytest

from app.facilitators.users.login_code_cap_alert_facilitator import describe_alert
from app.schemas.constants.users import LoginCodeCap
from app.schemas.dto.login_protection import LoginCodeCapAlert
from app.schemas.exceptions.login_errors import LoginCodeCapReachedError
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    PhoneNumberPrefix,
)
from app.schemas.typings.users.constrained_integers import OtpSendLimit
from app.use_cases.users.otp_login.login_code_conversion import find_number_range
from tests.users.accounts_phones import GERMANY_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

CODE_LIFETIME_SECONDS: int = 600
HOUR_SECONDS: int = 3600


def range_number(network: str, index: int) -> str:
    """A Georgian mobile in the range "+995<network>"."""

    return f"+995 {network} 12 34 {index:02d}"


def request_unused_codes(testbed: AccountsTestbed, network: str, count: int) -> None:
    for index in range(count):
        testbed.request_phone_code(range_number(network, index))


def test_a_range_whose_codes_go_unused_is_denied_for_the_hour() -> None:
    testbed = build_accounts_testbed()
    request_unused_codes(testbed, "555", 10)
    testbed.clock.advance(CODE_LIFETIME_SECONDS + 1)

    with pytest.raises(LoginCodeCapReachedError, match="Too many login codes"):
        testbed.request_phone_code(range_number("555", 99))

    assert testbed.cap_alerts.alerts == [
        LoginCodeCapAlert(
            cap=LoginCodeCap.NUMBER_RANGE_CONVERSION,
            limit=OtpSendLimit(1),
            country_code=CountryCode("GE"),
            phone_number_prefix=PhoneNumberPrefix("+995555"),
        )
    ]
    # Another range of the same country and other countries keep working.
    testbed.request_phone_code(range_number("577", 1))
    testbed.request_phone_code(GERMANY_MOBILE)

    testbed.clock.advance(HOUR_SECONDS)
    testbed.request_phone_code(range_number("555", 99))
    assert len(testbed.otp_delivery.deliveries) == 13


def test_codes_still_waiting_to_be_typed_do_not_count() -> None:
    testbed = build_accounts_testbed()
    request_unused_codes(testbed, "555", 10)

    testbed.clock.advance(CODE_LIFETIME_SECONDS - 60)
    testbed.request_phone_code(range_number("555", 99))

    assert testbed.cap_alerts.alerts == []


def test_a_range_whose_codes_are_used_stays_open() -> None:
    testbed = build_accounts_testbed()
    request_unused_codes(testbed, "555", 9)
    testbed.sign_in_with_phone(range_number("555", 50))
    testbed.clock.advance(CODE_LIFETIME_SECONDS + 1)

    testbed.request_phone_code(range_number("555", 99))

    assert testbed.cap_alerts.alerts == []


def test_a_country_whose_codes_go_unused_gets_a_lower_cap() -> None:
    testbed = build_accounts_testbed()
    for network in ("555", "577", "599"):
        request_unused_codes(testbed, network, 7)
    testbed.clock.advance(CODE_LIFETIME_SECONDS + 1)

    with pytest.raises(LoginCodeCapReachedError):
        testbed.request_phone_code(range_number("591", 1))

    assert testbed.cap_alerts.alerts == [
        LoginCodeCapAlert(
            cap=LoginCodeCap.COUNTRY_CONVERSION,
            limit=OtpSendLimit(10),
            country_code=CountryCode("GE"),
        )
    ]
    testbed.request_phone_code(GERMANY_MOBILE)
    testbed.clock.advance(HOUR_SECONDS)
    testbed.request_phone_code(range_number("591", 1))


def test_a_country_that_converts_keeps_its_cap() -> None:
    testbed = build_accounts_testbed()
    for index in range(10):
        testbed.sign_in_with_phone(range_number("599", index))
    for network in ("555", "577"):
        request_unused_codes(testbed, network, 7)
    testbed.clock.advance(CODE_LIFETIME_SECONDS + 1)

    testbed.request_phone_code(range_number("591", 1))

    assert testbed.cap_alerts.alerts == []


def test_verified_owners_are_never_throttled_by_conversion() -> None:
    testbed = build_accounts_testbed()
    testbed.sign_in_with_phone(range_number("555", 50))
    testbed.clock.advance(HOUR_SECONDS + 1)
    request_unused_codes(testbed, "555", 10)
    testbed.clock.advance(CODE_LIFETIME_SECONDS + 1)

    testbed.request_phone_code(range_number("555", 50))

    assert testbed.cap_alerts.alerts == []


def test_a_lower_configured_country_cap_refuses_first() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_COUNTRY_PER_HOUR": "5"})

    for index in range(5):
        testbed.request_phone_code(range_number("555", index))
    with pytest.raises(LoginCodeCapReachedError):
        testbed.request_phone_code(range_number("577", 1))

    assert [alert.cap for alert in testbed.cap_alerts.alerts] == [LoginCodeCap.COUNTRY]


def test_the_number_range_is_the_first_seven_characters() -> None:
    assert find_number_range("+995555123456") == PhoneNumberPrefix("+995555")


def test_a_denied_range_is_named_in_the_alert_line() -> None:
    alert = LoginCodeCapAlert(
        cap=LoginCodeCap.NUMBER_RANGE_CONVERSION,
        limit=OtpSendLimit(1),
        country_code=CountryCode("GE"),
        phone_number_prefix=PhoneNumberPrefix("+995555"),
    )

    line: str = describe_alert(alert)

    assert line.startswith(
        "Login code cap reached for GE (number range +995555): 1 login code to "
        "a number range whose codes go unused"
    )
