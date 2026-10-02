from hashlib import sha256

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.users import StartOtpLoginCommand, VerifyOtpLoginCommand
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    RateLimitedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress, OtpCode
from app.schemas.typings.users.prefixed_id import OtpChallengeId
from app.schemas.typings.users.strings import UserDisplayName
from app.utilities.security.access_tokens import hash_access_token
from tests.users.accounts_phones import (
    BRAZIL_MOBILE,
    GEORGIA_MOBILE,
    GERMANY_MOBILE,
    INDIA_MOBILE,
    ISRAEL_MOBILE,
    JAPAN_MOBILE,
    UAE_MOBILE,
    USA_MOBILE,
)
from tests.users.accounts_testbed import build_accounts_testbed


def wrong_code_for(correct_code: OtpCode) -> OtpCode:
    return OtpCode("000000" if correct_code != "000000" else "111111")


@pytest.mark.parametrize(
    ("raw_phone_number", "expected_country", "expected_locale"),
    [
        (GEORGIA_MOBILE, "GE", "ka"),
        (USA_MOBILE, "US", "en"),
        (BRAZIL_MOBILE, "BR", "pt-BR"),
        (INDIA_MOBILE, "IN", "en"),
        (GERMANY_MOBILE, "DE", "de"),
        (ISRAEL_MOBILE, "IL", "he"),
        (UAE_MOBILE, "AE", "ar"),
        (JAPAN_MOBILE, "JP", "ja"),
    ],
)
def test_first_login_creates_a_verified_user_in_the_country_language(
    raw_phone_number: str,
    expected_country: str,
    expected_locale: str,
) -> None:
    testbed = build_accounts_testbed()

    session = testbed.sign_in_with_phone(raw_phone_number)

    assert session.is_new_user is True
    assert session.user.login_method is LoginMethod.PHONE
    assert session.user.country_code == expected_country
    assert session.user.locale == expected_locale
    assert session.user.is_verified is True
    assert session.user.is_platform_admin is False
    assert session.user.phone_number is not None
    assert session.user.phone_number.startswith("+")
    stored_user = testbed.user_repo.get(session.user.id)
    assert stored_user is not None
    assert stored_user.is_verified is True
    assert stored_user.created_at == testbed.clock.now_microseconds()


def test_session_stores_only_the_token_hash_and_expires_after_the_lifetime() -> None:
    testbed = build_accounts_testbed()

    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    token_hash = hash_access_token(session.access_token)
    assert token_hash == sha256(session.access_token.encode()).hexdigest()
    assert str(token_hash) != str(session.access_token)
    assert len(session.access_token) >= 43
    stored_session = testbed.user_session_repo.find_by_token_hash(token_hash)
    assert stored_session is not None
    assert stored_session.user_id == session.user.id
    assert stored_session.token_hash == token_hash
    assert session.access_token not in stored_session.model_dump_json()
    thirty_days_in_microseconds = 30 * 24 * 60 * 60 * 1_000_000
    assert (
        session.expires_at
        == testbed.clock.now_microseconds() + thirty_days_in_microseconds
    )
    assert stored_session.expires_at == session.expires_at


def test_login_is_audited_with_the_client_address() -> None:
    testbed = build_accounts_testbed()
    challenge = testbed.request_phone_code(GEORGIA_MOBILE)

    session = testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=challenge.challenge_id,
            code=testbed.otp_delivery.last_code(),
            client_ip_address=ClientIpAddress("203.0.113.7"),
        )
    )

    login_entries = [
        entry
        for entry in testbed.audit_log_collection.list_all()
        if entry.action is AuditAction.LOGIN
    ]
    assert len(login_entries) == 1
    assert login_entries[0].actor_id == session.user.id
    assert login_entries[0].business_id is None
    assert login_entries[0].entity == "user"
    assert login_entries[0].entity_id == str(session.user.id)
    assert login_entries[0].ip_address == "203.0.113.7"


def test_second_login_finds_the_same_user_and_keeps_their_language() -> None:
    testbed = build_accounts_testbed()
    first_session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    testbed.clock.advance(60)
    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput("555 12 34 56"),
            country_hint=first_session.user.country_code,
            locale=LanguageTag("ru"),
        )
    )
    second_session = testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=challenge.challenge_id,
            code=testbed.otp_delivery.last_code(),
        )
    )

    assert second_session.is_new_user is False
    assert second_session.user.id == first_session.user.id
    assert second_session.user.locale == "ka"
    assert second_session.access_token != first_session.access_token


def test_new_user_gets_the_language_requested_with_the_code() -> None:
    testbed = build_accounts_testbed()
    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(
            phone_number=RawPhoneNumberInput(ISRAEL_MOBILE),
            locale=LanguageTag("ru"),
        )
    )

    session = testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=challenge.challenge_id,
            code=testbed.otp_delivery.last_code(),
        )
    )

    assert session.user.locale == "ru"
    assert session.user.country_code == "IL"


def test_email_login_creates_an_email_user_without_a_country() -> None:
    testbed = build_accounts_testbed()

    session = testbed.sign_in_with_email(" Owner@Example.com ")

    assert session.is_new_user is True
    assert session.user.login_method is LoginMethod.EMAIL
    assert session.user.email == "owner@example.com"
    assert session.user.phone_number is None
    assert session.user.country_code is None
    assert session.user.locale == "en"


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


def test_platform_admins_are_bootstrapped_from_settings() -> None:
    testbed = build_accounts_testbed(
        {
            "PLATFORM_ADMIN_EMAILS": "Dani@Example.com, ops@example.com",
            "PLATFORM_ADMIN_PHONE_NUMBERS": "+995555123456",
        }
    )

    email_admin = testbed.sign_in_with_email("DANI@example.com")
    phone_admin = testbed.sign_in_with_phone("555 12 34 56", "GE")
    regular_user = testbed.sign_in_with_phone(GERMANY_MOBILE)

    assert email_admin.user.is_platform_admin is True
    assert phone_admin.user.is_platform_admin is True
    assert regular_user.user.is_platform_admin is False


def test_platform_admin_flag_follows_the_settings_list() -> None:
    testbed = build_accounts_testbed()
    former_admin = UserDocument(
        login_method=LoginMethod.EMAIL,
        email=EmailAddress("former-admin@example.com"),
        locale=LanguageTag("en"),
        is_verified=True,
        is_platform_admin=True,
    )
    testbed.user_repo.save(former_admin)

    session = testbed.sign_in_with_email("former-admin@example.com")

    assert session.is_new_user is False
    assert session.user.id == former_admin.id
    assert session.user.is_platform_admin is False


def test_invited_unverified_user_becomes_verified_on_first_login() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(owner.user.id)
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=owner.user.id,
            business_id=business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(ISRAEL_MOBILE),
                display_name=UserDisplayName("Tamar"),
            ),
        )
    )
    invited_user = testbed.user_repo.find_by_phone_number(
        E164PhoneNumber("+972502345678")
    )
    assert invited_user is not None
    assert invited_user.is_verified is False

    session = testbed.sign_in_with_phone(ISRAEL_MOBILE)

    assert session.is_new_user is False
    assert session.user.id == invited_user.id
    assert session.user.is_verified is True
    assert session.user.display_name == "Tamar"
    assert session.user.locale == "ka"
