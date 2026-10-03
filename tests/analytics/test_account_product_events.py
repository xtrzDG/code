"""Signing up and in, a business created, the agreement accepted."""

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.dto.compliance import AcceptDpaCommand
from app.schemas.dto.users import StartOtpLoginCommand, VerifyOtpLoginCommand
from app.schemas.typings.analytics.constrained_strings import (
    LandingPath,
    UtmCampaign,
    UtmSource,
)
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.strings import RawEmailAddressInput
from tests.users.accounts_phones import GEORGIA_MOBILE
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed

CAMPAIGN = SignupAttribution(
    utm_source=UtmSource("instagram"),
    utm_campaign=UtmCampaign("autumn-launch"),
    landing_path=LandingPath("/"),
)


def sign_in(
    testbed: AccountsTestbed,
    email: str,
    attribution: SignupAttribution | None = None,
) -> None:
    testbed.clock.advance(60)
    challenge = testbed.start_otp_login.run(
        StartOtpLoginCommand(email=RawEmailAddressInput(email))
    )
    testbed.verify_otp_login.run(
        VerifyOtpLoginCommand(
            challenge_id=challenge.challenge_id,
            code=testbed.otp_delivery.last_code(),
            signup_attribution=attribution,
        )
    )


def test_the_first_sign_in_is_a_sign_up_then_only_sign_ins() -> None:
    testbed = build_accounts_testbed()

    sign_in(testbed, "owner@example.com")
    sign_in(testbed, "owner@example.com")

    assert testbed.product_events.names() == [
        ProductEventName.SIGNED_UP,
        ProductEventName.SIGNED_IN,
        ProductEventName.SIGNED_IN,
    ]
    user = testbed.user_repo.find_by_email(EmailAddress("owner@example.com"))
    assert user is not None
    assert {event.user_id for event in testbed.product_events.events} == {user.id}
    assert all(
        event.properties.login_method is LoginMethod.EMAIL
        for event in testbed.product_events.events
    )


def test_a_new_account_keeps_where_its_owner_came_from_once() -> None:
    testbed = build_accounts_testbed()

    sign_in(testbed, "owner@example.com", CAMPAIGN)
    sign_in(
        testbed,
        "owner@example.com",
        SignupAttribution(utm_source=UtmSource("google")),
    )

    user = testbed.user_repo.find_by_email(EmailAddress("owner@example.com"))
    assert user is not None
    assert user.signup_attribution == CAMPAIGN


def test_an_existing_account_ignores_a_later_attribution() -> None:
    testbed = build_accounts_testbed()
    sign_in(testbed, "owner@example.com")

    sign_in(testbed, "owner@example.com", CAMPAIGN)

    user = testbed.user_repo.find_by_email(EmailAddress("owner@example.com"))
    assert user is not None
    assert user.signup_attribution is None


def test_creating_a_business_reports_it_for_its_owner() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)

    business = testbed.create_restaurant(session.user.id)

    [created] = testbed.product_events.named(ProductEventName.BUSINESS_CREATED)
    assert created.user_id == session.user.id
    assert created.business_id == business.id
    assert created.occurred_at == business.created_at


def test_accepting_the_agreement_reports_its_version() -> None:
    testbed = build_accounts_testbed()
    session = testbed.sign_in_with_phone(GEORGIA_MOBILE)
    business = testbed.create_restaurant(session.user.id)

    testbed.accept_dpa.run(
        AcceptDpaCommand(user_id=session.user.id, business_id=business.id)
    )

    [accepted] = testbed.product_events.named(ProductEventName.DPA_ACCEPTED)
    assert accepted.business_id == business.id
    assert accepted.properties.dpa_version == testbed.settings.dpa_document_version
