"""
The platform team's partner list over the real API: adding partners and
codes, pausing, the monthly payout report and marking a month paid.
"""

from tests.e2e.harness import Workshop
from tests.referrals.referral_workshop import (
    accrue,
    add_partner,
    admin_headers,
    open_business,
    program,
)

OWNER_PHONE: str = "+995 555 12 34 56"


def test_the_team_adds_lists_and_pauses_a_partner(workshop: Workshop) -> None:
    admin = admin_headers(workshop)
    partner = add_partner(workshop, admin)
    assert partner["status"] == "active"
    assert partner["login_method"] == "phone"
    assert partner["phone_number"] == "+995599000111"
    assert [code["code"] for code in partner["codes"]] == ["agency-tbilisi"]

    listed = workshop.client.get("/v1/admin/partners", headers=admin)
    assert [item["partner_id"] for item in listed.json()["items"]] == [
        partner["partner_id"]
    ]

    paused = workshop.client.patch(
        f"/v1/admin/partners/{partner['partner_id']}",
        json={"status": "paused", "commission_rate_basis_points": 1500},
        headers=admin,
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"
    assert paused.json()["commission_rate_basis_points"] == 1500


def test_a_code_belongs_to_one_owner_only(workshop: Workshop) -> None:
    admin = admin_headers(workshop)
    partner = add_partner(workshop, admin)
    owner = open_business(workshop, OWNER_PHONE)
    business_code = program(workshop, owner)["code"]
    codes = f"/v1/admin/partners/{partner['partner_id']}/codes"

    added = workshop.client.post(codes, json={"code": "Agency-Batumi"}, headers=admin)
    assert added.status_code == 200, added.text
    assert [code["code"] for code in added.json()["codes"]] == [
        "agency-tbilisi",
        "Agency-Batumi",
    ]

    for taken in ("agency-batumi", business_code):
        refused = workshop.client.post(codes, json={"code": taken}, headers=admin)
        assert refused.status_code == 409, taken
        assert [reason["code"] for reason in refused.json()["reasons"]] == [
            "code_taken"
        ]

    again = workshop.client.post(
        "/v1/admin/partners",
        json={
            "name": "Second",
            "email": "second@example.com",
            "commission_rate_basis_points": 1000,
            "code": "agency-tbilisi",
        },
        headers=admin,
    )
    assert again.status_code == 409


def test_a_person_is_one_partner(workshop: Workshop) -> None:
    admin = admin_headers(workshop)
    add_partner(workshop, admin)

    twice = workshop.client.post(
        "/v1/admin/partners",
        json={
            "name": "Same person",
            "phone_number": "+995599000111",
            "commission_rate_basis_points": 1000,
            "code": "another-code",
        },
        headers=admin,
    )

    assert twice.status_code == 409


def test_the_month_is_reported_and_marked_paid_once(workshop: Workshop) -> None:
    admin = admin_headers(workshop)
    partner = add_partner(workshop, admin)
    owner = open_business(workshop, OWNER_PHONE, referral_code="agency-tbilisi")
    accrue(workshop, partner["partner_id"], owner.business_id, "2026-10", 10_340)
    accrue(workshop, partner["partner_id"], owner.business_id, "2026-10", 8_860)
    accrue(workshop, partner["partner_id"], owner.business_id, "2026-09", 500)

    report = workshop.client.get(
        "/v1/admin/partners/payouts", params={"month": "2026-10"}, headers=admin
    )
    assert report.status_code == 200, report.text
    [row] = report.json()["rows"]
    assert row["partner_name"] == "Tbilisi Digital"
    assert (row["accrued_minor"], row["accrued_invoices"]) == (19_200, 2)
    assert (row["paid_minor"], row["paid_invoices"]) == (0, 0)

    payouts = f"/v1/admin/partners/{partner['partner_id']}/payouts"
    body = {"month": "2026-10", "reference": "TBC transfer 42"}
    paid = workshop.client.post(payouts, json=body, headers=admin)
    assert paid.status_code == 200, paid.text
    assert paid.json()["paid_invoices"] == 2
    assert paid.json()["amounts"] == [{"amount_minor": 19_200, "currency_code": "GEL"}]

    [row] = workshop.client.get(
        "/v1/admin/partners/payouts", params={"month": "2026-10"}, headers=admin
    ).json()["rows"]
    assert (row["accrued_minor"], row["paid_minor"]) == (0, 19_200)
    assert workshop.client.post(payouts, json=body, headers=admin).status_code == 409


def test_a_bad_month_is_refused(workshop: Workshop) -> None:
    admin = admin_headers(workshop)

    response = workshop.client.get(
        "/v1/admin/partners/payouts", params={"month": "2026-13"}, headers=admin
    )

    assert response.status_code == 422


def test_owners_cannot_manage_partners(workshop: Workshop) -> None:
    owner = open_business(workshop, OWNER_PHONE)

    assert (
        workshop.client.get("/v1/admin/partners", headers=owner.headers).status_code
        == 403
    )
