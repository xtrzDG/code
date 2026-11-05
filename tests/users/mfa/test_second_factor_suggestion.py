"""
An owner without a second factor is asked to set one up at every sign-in
(`second_factor_suggested`: the cabinet shows a page they may skip) until
they do. A new account, a staff member and anyone who already signs in
with two factors is not asked; a business may still require a second
factor of its whole team (test_business_security.py).
"""

from app.schemas.typings.users.prefixed_id import UserId
from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE, sign_in_and_create_restaurant
from tests.users.mfa.mfa_api import (
    RESEND_WAIT_SECONDS,
    login_code_step,
    second_step,
    set_up_authenticator,
)

STAFF_PHONE: str = "+995 555 77 88 99"
BRAND_OWNER_PHONE: str = "+995 555 66 55 44"


def test_a_new_account_is_not_asked(workshop: Workshop) -> None:
    answer = login_code_step(workshop, "newcomer@cafe.example")

    assert answer["is_new_user"] is True
    assert answer["second_factor_suggested"] is False


def test_an_owner_is_asked_at_every_sign_in_until_they_set_one_up(
    workshop: Workshop,
) -> None:
    token, _, _ = sign_in_and_create_restaurant(workshop)
    first = login_code_step(workshop, GEORGIAN_OWNER_PHONE)
    # Put off: the next sign-in asks again.
    again = login_code_step(workshop, GEORGIAN_OWNER_PHONE)
    set_up_authenticator(workshop, str(again["access_token"]), GEORGIAN_OWNER_PHONE)
    with_app = login_code_step(workshop, GEORGIAN_OWNER_PHONE)
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    two_factors = second_step(
        workshop,
        with_app,
        code=workshop.authenticators.code_for(GEORGIAN_OWNER_PHONE, workshop.clock),
    )

    assert token
    assert first["second_factor_suggested"] is True
    assert again["second_factor_suggested"] is True
    assert with_app["mfa_required"] is True
    assert "second_factor_suggested" not in with_app
    assert two_factors.status_code == 200, two_factors.text
    assert two_factors.json()["second_factor_suggested"] is False


def test_staff_are_not_asked(workshop: Workshop) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    invited = workshop.client.post(
        f"/v1/businesses/{business_id}/members",
        json={"phone_number": STAFF_PHONE, "role": "staff"},
        headers=bearer(token),
    )

    staff = login_code_step(workshop, STAFF_PHONE)

    assert invited.status_code == 201, invited.text
    assert staff["second_factor_suggested"] is False


def test_a_brand_owner_without_a_business_of_their_own_is_asked(
    workshop: Workshop,
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    owner = bearer(token)
    brand = workshop.client.post(
        "/v1/brands",
        json={"name": "Salobie Group", "business_id": business_id},
        headers=owner,
    )
    invited = workshop.client.post(
        f"/v1/brands/{brand.json()['id']}/members",
        json={"phone_number": BRAND_OWNER_PHONE, "role": "brand_owner"},
        headers=owner,
    )

    brand_owner = login_code_step(workshop, BRAND_OWNER_PHONE)
    user_id = str(brand_owner["user"]["id"])
    businesses = workshop.container.repositories.business_repo().list_by_member(
        UserId(user_id)
    )

    assert brand.status_code == 201, brand.text
    assert invited.status_code == 201, invited.text
    # A member of no business: the brand alone makes them an owner.
    assert businesses == []
    assert brand_owner["second_factor_suggested"] is True
