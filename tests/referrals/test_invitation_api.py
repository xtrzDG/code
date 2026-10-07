"""
An owner's invitation over the real API: the link, who signed up by it,
and who may see it.
"""

from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.e2e.harness import Workshop
from tests.referrals.referral_workshop import (
    CABINET_BASE_URL,
    open_business,
    program,
    sign_up,
)

FIRST_OWNER: str = "+995 555 12 34 56"
INVITED_OWNER: str = "+995 555 65 43 21"
STAFF_PHONE: str = "+995 555 11 22 33"


def test_an_owner_gets_an_invitation_link_with_their_code(workshop: Workshop) -> None:
    owner = open_business(workshop, FIRST_OWNER)

    view = program(workshop, owner)

    code = view["code"]
    assert code
    assert view["invite_link"] == f"{CABINET_BASE_URL}/?ref={code}&src=invite"
    assert (view["invited"], view["paid"], view["rewarded"]) == (0, 0, 0)
    assert view["bookings_made"] == 0
    assert view["is_invite_card_due"] is False
    assert program(workshop, owner)["code"] == code


def test_a_business_signed_up_by_the_link_counts_as_invited(workshop: Workshop) -> None:
    owner = open_business(workshop, FIRST_OWNER)
    code = program(workshop, owner)["code"]

    invited = open_business(workshop, INVITED_OWNER, referral_code=code, name="Bia 2")

    assert program(workshop, owner)["invited"] == 1
    stored = workshop.container.repositories.business_repo().get(
        BusinessId(invited.business_id)
    )
    assert stored is not None and stored.referred_by is not None
    assert str(stored.referred_by.referring_business_id) == owner.business_id
    assert program(workshop, invited)["invited"] == 0


def test_a_code_in_any_letter_case_is_the_same_code(workshop: Workshop) -> None:
    owner = open_business(workshop, FIRST_OWNER)
    code = str(program(workshop, owner)["code"])

    open_business(workshop, INVITED_OWNER, referral_code=code.upper(), name="Bia 2")

    assert program(workshop, owner)["invited"] == 1


def test_an_owner_never_invites_their_own_next_business(workshop: Workshop) -> None:
    owner = open_business(workshop, FIRST_OWNER)
    code = program(workshop, owner)["code"]

    workshop.clock.advance(31)
    headers, _ = sign_up(workshop, FIRST_OWNER, referral_code=code)
    second = workshop.client.post(
        "/v1/businesses",
        json={"name": "Second place", "niche_key": "restaurant"},
        headers=headers,
    )

    assert second.status_code == 201, second.text
    assert program(workshop, owner)["invited"] == 0


def test_an_unknown_code_refers_nobody(workshop: Workshop) -> None:
    owner = open_business(workshop, FIRST_OWNER)
    program(workshop, owner)

    invited = open_business(workshop, INVITED_OWNER, referral_code="nobody-1")

    stored = workshop.container.repositories.business_repo().get(
        BusinessId(invited.business_id)
    )
    assert stored is not None and stored.referred_by is None
    assert program(workshop, owner)["invited"] == 0


def test_staff_do_not_see_the_invitation(workshop: Workshop) -> None:
    owner = open_business(workshop, FIRST_OWNER)
    invited = workshop.client.post(
        f"{owner.base}/members",
        json={"phone_number": STAFF_PHONE, "role": "staff"},
        headers=owner.headers,
    )
    assert invited.status_code == 201, invited.text
    staff, _ = sign_up(workshop, STAFF_PHONE)

    response = workshop.client.get(f"{owner.base}/referrals", headers=staff)

    assert response.status_code == 403
