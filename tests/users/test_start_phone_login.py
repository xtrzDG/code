"""Starting a phone login: numbers of any country, the channel and the locale."""

import pytest

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.dto.users import StartOtpLoginCommand
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.utilities.security.one_time_codes import hash_otp_code
from tests.users.accounts_phones import (
    BRAZIL_MOBILE,
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    INDIA_MOBILE,
    ISRAEL_MOBILE,
)
from tests.users.accounts_testbed import build_accounts_testbed


@pytest.mark.parametrize(
    (
        "raw_phone_number",
        "country_hint",
        "expected_e164",
        "expected_country",
        "expected_channel",
        "expected_locale",
        "expected_mask",
    ),
    [
        (
            GEORGIA_MOBILE,
            None,
            "+995555123456",
            "GE",
            OtpDeliveryChannel.SMS,
            "ka",
            "+995 *** ** ** 56",
        ),
        (
            "555 12 34 56",
            "GE",
            "+995555123456",
            "GE",
            OtpDeliveryChannel.SMS,
            "ka",
            "+995 *** ** ** 56",
        ),
        (
            "(201) 555-0123",
            "US",
            "+12015550123",
            "US",
            OtpDeliveryChannel.SMS,
            "en",
            "+1 ***-***-**23",
        ),
        (
            BRAZIL_MOBILE,
            None,
            "+5511961234567",
            "BR",
            OtpDeliveryChannel.WHATSAPP,
            "pt-BR",
            "+55 ** *****-**67",
        ),
        (
            INDIA_MOBILE,
            "GE",
            "+918123456789",
            "IN",
            OtpDeliveryChannel.SMS,
            "en",
            "+91 ***** ***89",
        ),
        (
            "01512 3456789",
            "DE",
            "+4915123456789",
            "DE",
            OtpDeliveryChannel.SMS,
            "de",
            "+49 **** *****89",
        ),
        (
            "050-234-5678",
            "IL",
            "+972502345678",
            "IL",
            OtpDeliveryChannel.WHATSAPP,
            "he",
            "+972 **-***-**78",
        ),
    ],
)
def test_phone_login_works_for_numbers_of_any_country(
    raw_phone_number: str,
    country_hint: str | None,
    expected_e164: str,
    expected_country: str,
    expected_channel: OtpDeliveryChannel,
    expected_locale: str,
    expected_mask: str,
) -> None:
    testbed = build_accounts_testbed()

    challenge = testbed.request_phone_code(raw_phone_number, country_hint)

    assert challenge.login_method is LoginMethod.PHONE
    assert challenge.phone_number == expected_e164
    assert challenge.country_code == expected_country
    assert challenge.delivery_channel is expected_channel
    assert challenge.locale == expected_locale
    assert challenge.masked_destination == expected_mask
    assert challenge.expires_in_seconds == 600
    assert challenge.international_phone_number is not None
    assert challenge.international_phone_number.startswith("+")

    delivery = testbed.otp_delivery.deliveries[-1]
    assert delivery.phone_number == expected_e164
    assert delivery.email is None
    assert delivery.delivery_channel is expected_channel
    assert delivery.language_tag == expected_locale
    assert len(delivery.code) == 6
    assert delivery.code.isdigit()

    stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
    assert stored is not None
    assert str(stored.code_hash) != str(delivery.code)
    assert stored.code_hash == hash_otp_code(stored.id, delivery.code)
    assert stored.created_at == testbed.clock.now_microseconds()
    assert stored.expires_at == testbed.clock.now_microseconds() + 600_000_000
    assert stored.failed_attempts == 0
    assert stored.is_consumed is False


@pytest.mark.parametrize(
    ("raw_phone_number", "requested_channel", "expected_channel"),
    [
        (GEORGIA_MOBILE, OtpDeliveryChannel.WHATSAPP, OtpDeliveryChannel.WHATSAPP),
        (GEORGIA_MOBILE, OtpDeliveryChannel.TELEGRAM, OtpDeliveryChannel.TELEGRAM),
        (GERMANY_MOBILE, OtpDeliveryChannel.WHATSAPP, OtpDeliveryChannel.SMS),
        (BRAZIL_MOBILE, OtpDeliveryChannel.EMAIL, OtpDeliveryChannel.WHATSAPP),
        (ISRAEL_MOBILE, OtpDeliveryChannel.SMS, OtpDeliveryChannel.SMS),
    ],
)
def test_requested_channel_is_used_only_when_the_country_supports_it(
    raw_phone_number: str,
    requested_channel: OtpDeliveryChannel,
    expected_channel: OtpDeliveryChannel,
) -> None:
    testbed = build_accounts_testbed()

    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput(raw_phone_number),
            preferred_delivery_channel=requested_channel,
        )
    )

    assert challenge.delivery_channel is expected_channel
    assert testbed.otp_delivery.deliveries[-1].delivery_channel is expected_channel


def test_requested_locale_wins_and_must_be_a_known_language() -> None:
    testbed = build_accounts_testbed()

    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput(ISRAEL_MOBILE),
            locale=LanguageTag("ar"),
        )
    )

    assert challenge.locale == "ar"
    assert testbed.otp_delivery.deliveries[-1].language_tag == "ar"

    with pytest.raises(UnsupportedLanguageError):
        testbed.start_otp_login.run(
            StartOtpLoginCommand(
                phone_number=RawPhoneNumberInput(GEORGIA_MOBILE),
                locale=LanguageTag("xh"),
            )
        )
