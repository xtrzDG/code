import pytest

from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.businesses import InviteStaffCommand, InviteStaffRequest
from app.schemas.dto.users import LogoutCommand, UpdateCurrentUserCommand
from app.schemas.exceptions.application_errors import (
    AuthenticationRequiredError,
    NotFoundError,
    UnsupportedLanguageError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken, UserDisplayName
from app.utilities.security.access_tokens import hash_access_token
from tests.users.accounts_phones import GEORGIA_MOBILE, ISRAEL_MOBILE
from tests.users.accounts_testbed import build_accounts_testbed

THIRTY_DAYS_IN_SECONDS: int = 30 * 24 * 60 * 60


def test_valid_token_authenticates_its_user() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    assert testbed.authenticate_user.run(session.access_token) == session.user.id


def test_unknown_token_is_refused() -> None:
    testbed = build_accounts_testbed()
    testbed.sign_in_with_phone(GEORGIA_MOBILE)

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(AccessToken("forged-token"))


def test_expired_session_is_refused_and_removed() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    testbed.clock.advance(THIRTY_DAYS_IN_SECONDS - 1)
    assert testbed.authenticate_user.run(session.access_token) == session.user.id

    testbed.clock.advance(1)
    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(session.access_token)

    token_hash = hash_access_token(session.access_token)
    assert testbed.user_session_repo.find_by_token_hash(token_hash) is None


def test_session_lifetime_comes_from_settings() -> None:
    testbed = build_accounts_testbed({"SESSION_LIFETIME_SECONDS": "3600"})
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    testbed.clock.advance(3600)

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(session.access_token)


def test_session_of_a_deleted_user_is_refused() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.user_collection.delete(str(session.user.id))

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(session.access_token)


def test_logout_ends_only_the_current_session() -> None:
    testbed = build_accounts_testbed()
    first_session = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.clock.advance(60)
    second_session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    testbed.logout.run(LogoutCommand(access_token=first_session.access_token))

    with pytest.raises(AuthenticationRequiredError):
        testbed.authenticate_user.run(first_session.access_token)
    assert (
        testbed.authenticate_user.run(second_session.access_token)
        == second_session.user.id
    )
    with pytest.raises(AuthenticationRequiredError):
        testbed.logout.run(LogoutCommand(access_token=first_session.access_token))


def test_current_user_lists_owned_and_staff_memberships() -> None:
    testbed = build_accounts_testbed()
    owner = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    colleague = testbed.sign_in_with_phone(ISRAEL_MOBILE)
    own_business = testbed.create_restaurant(owner.user.id, "Khinkali House")
    testbed.clock.advance(1)
    foreign_business = testbed.create_restaurant(colleague.user.id, "Falafel Bar")
    testbed.invite_staff.run(
        InviteStaffCommand(
            user_id=colleague.user.id,
            business_id=foreign_business.id,
            invitation=InviteStaffRequest(
                phone_number=RawPhoneNumberInput(GEORGIA_MOBILE)
            ),
        )
    )

    current_user = testbed.get_current_user.run(owner.user.id)

    assert current_user.user.id == owner.user.id
    assert [
        (membership.business_id, membership.role, membership.business_name)
        for membership in current_user.memberships
    ] == [
        (own_business.id, BusinessMemberRole.OWNER, "Khinkali House"),
        (foreign_business.id, BusinessMemberRole.STAFF, "Falafel Bar"),
    ]
    assert current_user.memberships[0].country_code == "GE"


def test_current_user_of_unknown_id_is_not_found() -> None:
    testbed = build_accounts_testbed()

    with pytest.raises(NotFoundError):
        testbed.get_current_user.run(UserId())


@pytest.mark.parametrize(
    ("display_name", "locale"),
    [
        ("ნინო", "ka"),
        ("נועה", "he"),
        ("فاطمة", "ar"),
        ("Анна", "ru"),
        ("さくら", "ja"),
    ],
)
def test_profile_accepts_names_and_languages_of_any_script(
    display_name: str,
    locale: str,
) -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    updated_user = testbed.update_current_user.run(
        UpdateCurrentUserCommand(
            user_id=session.user.id,
            display_name=UserDisplayName(display_name),
            locale=LanguageTag(locale),
        )
    )

    assert updated_user.display_name == display_name
    assert updated_user.locale == locale
    stored_user = testbed.user_repo.get(session.user.id)
    assert stored_user is not None
    assert stored_user.display_name == display_name
    assert stored_user.locale == locale


def test_missing_fields_stay_and_blank_name_clears() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    testbed.update_current_user.run(
        UpdateCurrentUserCommand(
            user_id=session.user.id,
            display_name=UserDisplayName("Giorgi"),
        )
    )

    unchanged_user = testbed.update_current_user.run(
        UpdateCurrentUserCommand(user_id=session.user.id)
    )
    cleared_user = testbed.update_current_user.run(
        UpdateCurrentUserCommand(
            user_id=session.user.id,
            display_name=UserDisplayName("   "),
        )
    )

    assert unchanged_user.display_name == "Giorgi"
    assert unchanged_user.locale == "ka"
    assert cleared_user.display_name is None


def test_profile_rejects_unknown_languages_and_overlong_names() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    with pytest.raises(UnsupportedLanguageError):
        testbed.update_current_user.run(
            UpdateCurrentUserCommand(
                user_id=session.user.id,
                locale=LanguageTag("xh"),
            )
        )

    with pytest.raises(ValidationFailedError):
        testbed.update_current_user.run(
            UpdateCurrentUserCommand(
                user_id=session.user.id,
                display_name=UserDisplayName("x" * 101),
            )
        )

    with pytest.raises(NotFoundError):
        testbed.update_current_user.run(UpdateCurrentUserCommand(user_id=UserId()))
