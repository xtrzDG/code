import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.constants.users import LoginMethod
from app.schemas.dto.users import StartOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    CountryRestrictedError,
    ExternalServiceError,
    InvalidPhoneNumberError,
    RateLimitedError,
    UnknownCountryError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from app.utilities.security.one_time_codes import hash_otp_code
from tests.users.accounts_phones import (
    BRAZIL_MOBILE,
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    INDIA_MOBILE,
    IRAN_MOBILE,
    ISRAEL_MOBILE,
    MONACO_MOBILE,
    NORTH_KOREA_MOBILE,
)
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


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


def test_repeated_request_for_the_same_destination_is_throttled() -> None:
    testbed = build_accounts_testbed()
    testbed.request_phone_code(GEORGIA_MOBILE)

    testbed.clock.advance(29)
    with pytest.raises(RateLimitedError):
        testbed.request_phone_code("555 12 34 56", "GE")

    testbed.request_phone_code(GERMANY_MOBILE)

    testbed.clock.advance(2)
    second_challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    assert second_challenge.phone_number == "+995555123456"
    assert len(testbed.otp_delivery.deliveries) == 3


def test_repeated_email_request_is_throttled_case_insensitively() -> None:
    testbed = build_accounts_testbed()
    testbed.start_otp_login.run(
        StartOtpLoginCommand(email=RawEmailAddressInput("OWNER@example.com"))
    )

    with pytest.raises(RateLimitedError):
        testbed.start_otp_login.run(
            StartOtpLoginCommand(email=RawEmailAddressInput("owner@EXAMPLE.com"))
        )


def test_failed_delivery_stores_nothing_and_allows_an_immediate_retry() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.is_failing = True

    with pytest.raises(ExternalServiceError):
        testbed.request_phone_code(GEORGIA_MOBILE)

    assert (
        testbed.otp_challenge_repo.list_created_since(
            testbed.clock.microseconds_ago(60)
        )
        == []
    )

    testbed.otp_delivery.is_failing = False
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    assert testbed.otp_challenge_repo.get(challenge.challenge_id) is not None


def test_only_channels_with_a_provider_are_picked() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.channels = frozenset({OtpDeliveryChannel.TELEGRAM})

    challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    assert challenge.delivery_channel is OtpDeliveryChannel.TELEGRAM
    assert testbed.otp_delivery.attempted_channels == [OtpDeliveryChannel.TELEGRAM]


def test_a_failing_provider_falls_back_along_the_country_list() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.failing_channels = {
        OtpDeliveryChannel.TELEGRAM,
        OtpDeliveryChannel.SMS,
    }

    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput(GEORGIA_MOBILE),
            preferred_delivery_channel=OtpDeliveryChannel.TELEGRAM,
        )
    )

    assert challenge.delivery_channel is OtpDeliveryChannel.WHATSAPP
    assert testbed.otp_delivery.attempted_channels == [
        OtpDeliveryChannel.TELEGRAM,
        OtpDeliveryChannel.SMS,
        OtpDeliveryChannel.WHATSAPP,
    ]
    stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
    assert stored is not None
    assert stored.delivery_channel is OtpDeliveryChannel.WHATSAPP
    [delivery] = testbed.otp_delivery.deliveries
    assert stored.code_hash == hash_otp_code(stored.id, delivery.code)


def test_when_every_provider_fails_a_generic_error_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.failing_channels = set(OtpDeliveryChannel)

    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(
            ExternalServiceError, match="could not send a login code"
        ) as raised,
    ):
        testbed.request_phone_code(GEORGIA_MOBILE)

    # Provider names and settings stay in the server log.
    assert "provider is down" not in str(raised.value)
    for channel in ("sms", "whatsapp", "telegram"):
        assert f"{channel} provider is down" in caplog.text
    assert len(testbed.otp_delivery.attempted_channels) == 3
    assert (
        testbed.otp_challenge_repo.list_created_since(
            testbed.clock.microseconds_ago(60)
        )
        == []
    )


def test_phone_login_without_any_phone_provider_suggests_email() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.channels = frozenset({OtpDeliveryChannel.EMAIL})

    with pytest.raises(ExternalServiceError, match="Sign in with e-mail"):
        testbed.request_phone_code(GERMANY_MOBILE)

    assert testbed.otp_delivery.attempted_channels == []


def test_email_login_needs_an_email_provider() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.channels = frozenset({OtpDeliveryChannel.SMS})

    with pytest.raises(ExternalServiceError, match="no e-mail provider"):
        testbed.start_otp_login.run(
            StartOtpLoginCommand(email=RawEmailAddressInput("owner@example.com"))
        )

    assert testbed.otp_delivery.attempted_channels == []


def test_parallel_requests_for_one_number_send_one_code() -> None:
    testbed = build_accounts_testbed()
    deliver = testbed.otp_delivery.deliver

    def slow_deliver(*args: Any, **kwargs: Any) -> None:
        time.sleep(0.2)  # a provider round trip
        deliver(*args, **kwargs)

    testbed.otp_delivery.deliver = slow_deliver  # type: ignore[method-assign]

    def request(_: int) -> str:
        try:
            testbed.request_phone_code(GEORGIA_MOBILE)
        except RateLimitedError:
            return "limited"
        return "sent"

    with ThreadPoolExecutor(max_workers=10) as pool:
        outcomes = list(pool.map(request, range(10)))

    assert sorted(outcomes) == ["limited"] * 9 + ["sent"]
    assert len(testbed.otp_delivery.deliveries) == 1


def georgian_number(index: int) -> str:
    return f"+995 555 12 34 {index:02d}"


def request_from(
    testbed: AccountsTestbed, raw_phone_number: str, ip_address: str
) -> None:
    testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput(raw_phone_number),
            client_ip_address=ClientIpAddress(ip_address),
        )
    )


def test_one_address_cannot_request_codes_for_many_numbers() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_IP_PER_HOUR": "3"})
    for index in range(3):
        request_from(testbed, georgian_number(index), "203.0.113.7")

    with pytest.raises(RateLimitedError, match="Too many login codes"):
        request_from(testbed, georgian_number(3), "203.0.113.7")

    request_from(testbed, georgian_number(4), "198.51.100.1")
    assert len(testbed.otp_delivery.deliveries) == 4
    testbed.clock.advance(3601)
    request_from(testbed, georgian_number(5), "203.0.113.7")


def test_one_number_gets_a_limited_number_of_codes_an_hour() -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_DESTINATION_PER_HOUR": "2"})
    testbed.request_phone_code(GEORGIA_MOBILE)
    testbed.clock.advance(31)
    testbed.request_phone_code(GEORGIA_MOBILE)
    testbed.clock.advance(31)

    with pytest.raises(RateLimitedError, match="Too many login codes"):
        testbed.request_phone_code(GEORGIA_MOBILE)

    assert len(testbed.otp_delivery.deliveries) == 2


def test_the_hourly_cap_stops_all_sends(caplog: pytest.LogCaptureFixture) -> None:
    testbed = build_accounts_testbed({"OTP_SENDS_PER_HOUR": "2"})
    testbed.request_phone_code(georgian_number(1))
    testbed.request_phone_code(georgian_number(2))

    with caplog.at_level(logging.WARNING), pytest.raises(RateLimitedError):
        testbed.request_phone_code(georgian_number(3))

    assert "hourly cap" in caplog.text
    assert len(testbed.otp_delivery.deliveries) == 2


def test_a_failed_delivery_releases_the_reservation() -> None:
    testbed = build_accounts_testbed()
    testbed.otp_delivery.is_failing = True
    with pytest.raises(ExternalServiceError):
        testbed.request_phone_code(GEORGIA_MOBILE)

    testbed.otp_delivery.is_failing = False
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    assert challenge.delivery_channel is OtpDeliveryChannel.SMS
    assert len(testbed.otp_delivery.deliveries) == 1


def test_switching_channel_skips_the_resend_wait() -> None:
    # Brazil sends by WhatsApp first; a number without WhatsApp gets nothing,
    # so the code screen offers SMS at once.
    testbed = build_accounts_testbed()

    def request(channel: OtpDeliveryChannel | None) -> OtpDeliveryChannel:
        return testbed.start_otp_login.run(
            StartOtpLoginCommand(
                phone_number=RawPhoneNumberInput(BRAZIL_MOBILE),
                preferred_delivery_channel=channel,
            )
        ).delivery_channel

    assert request(None) is OtpDeliveryChannel.WHATSAPP
    assert request(OtpDeliveryChannel.SMS) is OtpDeliveryChannel.SMS
    assert testbed.otp_delivery.deliveries[-1].delivery_channel is (
        OtpDeliveryChannel.SMS
    )
    with pytest.raises(RateLimitedError):
        request(OtpDeliveryChannel.SMS)
    with pytest.raises(RateLimitedError):
        request(None)
    with pytest.raises(RateLimitedError):
        request(OtpDeliveryChannel.WHATSAPP)
