"""Verifying a login code: users, sessions, audit and platform admins."""

from hashlib import sha256

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.users import UserDocument
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.mfa_login import MfaRequiredView
from app.schemas.dto.users import StartOtpLoginCommand, VerifyOtpLoginCommand
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.constrained_strings import EmailAddress
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

    session = testbed.expect_session(
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=testbed.otp_delivery.last_code(),
                client_ip_address=ClientIpAddress("203.0.113.7"),
            )
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
    second_session = testbed.expect_session(
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=testbed.otp_delivery.last_code(),
            )
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

    session = testbed.expect_session(
        testbed.verify_otp_login.run(
            VerifyOtpLoginCommand(
                challenge_id=challenge.challenge_id,
                code=testbed.otp_delivery.last_code(),
            )
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


def test_platform_admins_are_bootstrapped_from_settings() -> None:
    testbed = build_accounts_testbed(
        {
            "PLATFORM_ADMIN_EMAILS": "Dani@Example.com, ops@example.com",
            "PLATFORM_ADMIN_PHONE_NUMBERS": "+995555123456",
        }
    )

    email_admin = testbed.verify_email_code("DANI@example.com")
    phone_admin = testbed.verify_phone_code("555 12 34 56", "GE")
    regular_user = testbed.sign_in_with_phone(GERMANY_MOBILE)

    # Admins always take the second step: setting up an authenticator first.
    for answer in (email_admin, phone_admin):
        assert isinstance(answer, MfaRequiredView)
        assert answer.mfa_challenge.requires_enrollment is True
    admins = [
        testbed.user_repo.find_by_email(EmailAddress("dani@example.com")),
        testbed.user_repo.find_by_phone_number(E164PhoneNumber("+995555123456")),
    ]
    assert [admin is not None and admin.is_platform_admin for admin in admins] == [
        True,
        True,
    ]
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
