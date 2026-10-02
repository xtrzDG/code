"""Starting an email login, and the login requests that are refused."""

import pytest

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.dto.users import StartOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    CountryRestrictedError,
    InvalidPhoneNumberError,
    UnknownCountryError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from tests.users.accounts_phones import (
    GEORGIA_MOBILE,
    IRAN_MOBILE,
    MONACO_MOBILE,
    NORTH_KOREA_MOBILE,
)
from tests.users.accounts_testbed import build_accounts_testbed


def test_email_login_normalizes_the_address_and_masks_it() -> None:
    testbed = build_accounts_testbed()

    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(email=RawEmailAddressInput("  Owner@Example.COM "))
    )

    assert challenge.login_method is LoginMethod.EMAIL
    assert challenge.delivery_channel is OtpDeliveryChannel.EMAIL
    assert challenge.masked_destination == "o***r@example.com"
    assert challenge.locale == "en"
    assert challenge.phone_number is None
    assert challenge.country_code is None
    delivery = testbed.otp_delivery.deliveries[-1]
    assert delivery.email == "owner@example.com"
    assert delivery.phone_number is None


def test_email_login_with_a_country_hint_uses_its_owner_language() -> None:
    testbed = build_accounts_testbed()

    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(
            email=RawEmailAddressInput("nino@example.ge"),
            country_hint=CountryCode("GE"),
        )
    )

    assert challenge.locale == "ka"
    assert challenge.country_code == "GE"
    stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
    assert stored is not None
    assert stored.country_code == "GE"


def test_internationalized_email_domains_are_stored_in_ascii_form() -> None:
    testbed = build_accounts_testbed()

    testbed.start_otp_login.run(
        StartOtpLoginCommand(email=RawEmailAddressInput("Owner@Пример.РФ"))
    )

    assert testbed.otp_delivery.deliveries[-1].email == "owner@xn--e1afmkfd.xn--p1ai"


@pytest.mark.parametrize(
    ("command", "expected_error"),
    [
        (
            StartOtpLoginCommand(
                phone_number=RawPhoneNumberInput(GEORGIA_MOBILE),
                email=RawEmailAddressInput("owner@example.com"),
            ),
            ValidationFailedError,
        ),
        (StartOtpLoginCommand(), ValidationFailedError),
        (
            StartOtpLoginCommand(phone_number=RawPhoneNumberInput("12345")),
            InvalidPhoneNumberError,
        ),
        (
            StartOtpLoginCommand(phone_number=RawPhoneNumberInput("555 12 34 56")),
            InvalidPhoneNumberError,
        ),
        (
            StartOtpLoginCommand(email=RawEmailAddressInput("not-an-email")),
            ValidationFailedError,
        ),
        (
            StartOtpLoginCommand(email=RawEmailAddressInput("owner@localhost")),
            ValidationFailedError,
        ),
        (
            StartOtpLoginCommand(phone_number=RawPhoneNumberInput("+995 32 212 34 56")),
            ValidationFailedError,
        ),
        (
            StartOtpLoginCommand(phone_number=RawPhoneNumberInput("+1 800-234-5678")),
            ValidationFailedError,
        ),
        (
            StartOtpLoginCommand(
                email=RawEmailAddressInput("owner@example.com"),
                country_hint=CountryCode("ZZ"),
            ),
            UnknownCountryError,
        ),
    ],
)
def test_invalid_login_requests_are_rejected_without_sending_a_code(
    command: StartOtpLoginCommand,
    expected_error: type[Exception],
) -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(expected_error):
        testbed.start_otp_login.run(command)

    assert testbed.otp_delivery.deliveries == []


def test_restricted_countries_cannot_sign_up() -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(CountryRestrictedError):
        testbed.request_phone_code(NORTH_KOREA_MOBILE)

    with pytest.raises(CountryRestrictedError):
        testbed.request_phone_code(IRAN_MOBILE)

    with pytest.raises(CountryRestrictedError):
        testbed.start_otp_login.run(
            StartOtpLoginCommand(
                email=RawEmailAddressInput("someone@example.com"),
                country_hint=CountryCode("KP"),
            )
        )

    assert testbed.otp_delivery.deliveries == []


def test_settings_restriction_list_can_be_emptied() -> None:
    testbed = build_accounts_testbed({"RESTRICTED_COUNTRY_CODES": ""})

    challenge = testbed.request_phone_code(IRAN_MOBILE)

    assert challenge.country_code == "IR"
    assert challenge.locale == "fa"

    with pytest.raises(CountryRestrictedError):
        testbed.request_phone_code(NORTH_KOREA_MOBILE)


def test_country_without_phone_code_channels_asks_for_email() -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(ValidationFailedError, match="e-mail"):
        testbed.request_phone_code(MONACO_MOBILE)
