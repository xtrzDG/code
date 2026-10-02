"""Throttling login codes per destination, per client address and per hour."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.users import StartOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from tests.users.accounts_phones import BRAZIL_MOBILE, GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


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
