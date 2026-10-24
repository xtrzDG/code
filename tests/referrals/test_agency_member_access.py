"""
An agency member: an outside helper the owner let into the team. They do
staff's work and build the assistant; billing, the team and copies of the
customers' data stay the owner's.
"""

from tests.e2e.harness import Workshop
from tests.referrals.referral_workshop import Owner, open_business, sign_up

OWNER_PHONE: str = "+995 555 12 34 56"
AGENCY_PHONE: str = "+995 555 77 88 99"


def agency_member(workshop: Workshop, owner: Owner) -> dict[str, str]:
    invited = workshop.client.post(
        f"{owner.base}/members",
        json={"phone_number": AGENCY_PHONE, "role": "agency"},
        headers=owner.headers,
    )
    assert invited.status_code == 201, invited.text
    headers, _ = sign_up(workshop, AGENCY_PHONE)
    return headers


def test_an_agency_member_cannot_see_billing(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)
    agency = agency_member(workshop, owner)

    for path in ("/billing", "/billing/profile", "/referrals"):
        response = workshop.client.get(f"{owner.base}{path}", headers=agency)
        assert response.status_code == 403, path

    assert (
        workshop.client.get(f"{owner.base}/billing", headers=owner.headers).status_code
        == 200
    )


def test_an_agency_member_builds_the_assistant(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)
    agency = agency_member(workshop, owner)

    saved = workshop.client.patch(
        f"{owner.base}/profile",
        json={"hours": [{"weekday": 1, "opens_at": 540, "closes_at": 1080}]},
        headers=agency,
    )

    assert saved.status_code == 200, saved.text
    business = workshop.client.get(owner.base, headers=agency)
    assert business.status_code == 200
    assert business.json()["viewer_role"] == "agency"


def test_an_agency_member_cannot_copy_customers_out(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)
    agency = agency_member(workshop, owner)

    exported = workshop.client.get(f"{owner.base}/exports/bookings", headers=agency)

    assert exported.status_code == 403


def test_an_agency_member_cannot_change_the_team(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)
    agency = agency_member(workshop, owner)

    invited = workshop.client.post(
        f"{owner.base}/members",
        json={"phone_number": "+995 555 00 11 22", "role": "staff"},
        headers=agency,
    )

    assert invited.status_code == 403
