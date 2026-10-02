"""Which login codes are accepted: wrong, expired, reused or foreign codes."""

import pytest

from app.schemas.dto.users import VerifyOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from tests.users.accounts_phones import GEORGIA_MOBILE, GERMANY_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed


def wrong_code_for(correct_code: OtpCode) -> OtpCode:
    return OtpCode("000000" if correct_code != "000000" else "111111")


def test_wrong_codes_count_and_lock_the_challenge() -> None:
    testbed = build_accounts_testbed({"OTP_MAX_FAILED_ATTEMPTS": "3"})
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()

    for expected_attempts in (1, 2, 3):
        with pytest.raises(AuthenticationRequiredError):
            testbed.verify_otp_login.run(
                VerifyOtpLoginCommand(
                    challenge_id=challenge.challenge_id,
                    code=wrong_code_for(correct_code),
                )
            )

        stored = testbed.otp_challenge_repo.get(challenge.challenge_id)
        assert stored is not None
        assert stored.failed_attempts == expected_attempts

    with pytest.raises(RateLimitedError):
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=correct_code,
            )
        )

    assert (
        testbed.user_repo.find_by_phone_number(E164PhoneNumber("+995555123456")) is None
    )


def test_right_code_after_some_wrong_ones_still_signs_in() -> None:
    testbed = build_accounts_testbed()
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    correct_code = testbed.otp_delivery.last_code()
    with pytest.raises(AuthenticationRequiredError):
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=wrong_code_for(correct_code),
            )
        )

    session = testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(challenge_id=challenge.challenge_id, code=correct_code)
    )

    assert session.user.phone_number == "+995555123456"


def test_expired_code_is_refused() -> None:
    testbed = build_accounts_testbed({"OTP_LIFETIME_SECONDS": "120"})
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    testbed.clock.advance(120)

    with pytest.raises(AuthenticationRequiredError):
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=testbed.otp_delivery.last_code(),
            )
        )


def test_code_valid_until_just_before_expiry() -> None:
    testbed = build_accounts_testbed({"OTP_LIFETIME_SECONDS": "120"})
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    testbed.clock.advance(119)
    session = testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=challenge.challenge_id,
            code=testbed.otp_delivery.last_code(),
        )
    )

    assert session.is_new_user is True


def test_code_cannot_be_used_twice() -> None:
    testbed = build_accounts_testbed()
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    command = VerifyOtpLoginCommand(
        challenge_id=challenge.challenge_id,
        code=testbed.otp_delivery.last_code(),
    )
    testbed.verify_otp_login.run(command)

    with pytest.raises(AuthenticationRequiredError):
        testbed.verify_otp_login.run(command)


def test_unknown_challenge_is_refused() -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(AuthenticationRequiredError):
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=OtpChallengeId(),
                code=OtpCode("123456"),
            )
        )


def test_code_of_one_challenge_does_not_open_another() -> None:
    testbed = build_accounts_testbed()
    georgian_challenge = testbed.request_phone_code(GEORGIA_MOBILE)
    georgian_code = testbed.otp_delivery.last_code()
    german_challenge = testbed.request_phone_code(GERMANY_MOBILE)
    german_code = testbed.otp_delivery.last_code()
    if german_code == georgian_code:
        pytest.skip("Both random codes are equal; nothing to compare.")

    with pytest.raises(AuthenticationRequiredError):
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=german_challenge.challenge_id,
                code=georgian_code,
            )
        )

    session = testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=georgian_challenge.challenge_id,
            code=georgian_code,
        )
    )
    assert session.user.country_code == "GE"
