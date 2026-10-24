"""Which provider sends the login code, and what happens when providers fail."""

import logging

import pytest

from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.dto.users import StartOtpLoginCommand
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.strings import RawEmailAddressInput
from app.utilities.security.one_time_codes import hash_otp_code
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


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
