"""
A partner over the real API: added by the platform team, signs in with the
phone number on file, sees the businesses their link brought and their
commissions.
"""

from tests.e2e.harness import Workshop
from tests.referrals.referral_workshop import (
    CABINET_BASE_URL,
    PARTNER_PHONE,
    accrue,
    add_partner,
    admin_headers,
    open_business,
    sign_up,
)

OWNER_PHONE: str = "+995 555 12 34 56"


def test_a_partner_sees_their_link_businesses_and_commissions(
    workshop: Workshop,
) -> None:
    partner = add_partner(workshop, admin_headers(workshop))
    owner = open_business(workshop, OWNER_PHONE, referral_code="agency-tbilisi")
    accrue(workshop, partner["partner_id"], owner.business_id, "2026-10", 10_340)

    headers, _ = sign_up(workshop, PARTNER_PHONE)
    me = workshop.client.get("/v1/me", headers=headers)
    assert me.json()["is_partner"] is True

    portal = workshop.client.get("/v1/partner", headers=headers)
    assert portal.status_code == 200, portal.text
    body = portal.json()
    assert body["name"] == "Tbilisi Digital"
    assert body["commission_rate_basis_points"] == 2000
    assert body["codes"] == [
        {
            "code": "agency-tbilisi",
            "link": f"{CABINET_BASE_URL}/?ref=agency-tbilisi&src=partner",
        }
    ]
    assert (body["referred_businesses"], body["paid_businesses"]) == (1, 0)
    assert body["totals"] == [
        {
            "currency_code": "GEL",
            "status": "accrued",
            "invoice_count": 1,
            "amount_minor": 10_340,
        }
    ]

    referrals = workshop.client.get("/v1/partner/referrals", headers=headers).json()
    [referred] = referrals["items"]
    assert referred["business_id"] == owner.business_id
    assert referred["business_name"] == "Salobie Bia"
    assert referred["code"] == "agency-tbilisi"
    assert referred["first_paid_at"] is None

    commissions = workshop.client.get("/v1/partner/commissions", headers=headers)
    [entry] = commissions.json()["items"]
    assert entry["business_name"] == "Salobie Bia"
    assert (entry["month"], entry["amount_minor"]) == ("2026-10", 10_340)


def test_someone_who_is_not_a_partner_gets_no_portal(workshop: Workshop) -> None:
    headers, _ = sign_up(workshop, OWNER_PHONE)

    assert workshop.client.get("/v1/me", headers=headers).json()["is_partner"] is False
    for path in ("/v1/partner", "/v1/partner/referrals", "/v1/partner/commissions"):
        assert workshop.client.get(path, headers=headers).status_code == 404


def test_a_partners_own_business_is_not_their_referral(workshop: Workshop) -> None:
    add_partner(workshop, admin_headers(workshop))

    own = open_business(workshop, PARTNER_PHONE, referral_code="agency-tbilisi")

    portal = workshop.client.get("/v1/partner", headers=own.headers).json()
    assert portal["referred_businesses"] == 0
