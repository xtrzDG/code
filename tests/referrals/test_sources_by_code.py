"""The founder's sources table splits sign-ups by the referral code."""

from tests.e2e.harness import Workshop
from tests.referrals.referral_workshop import (
    add_partner,
    admin_headers,
    open_business,
    program,
)


def test_sign_ups_are_counted_per_referral_code(workshop: Workshop) -> None:
    admin = admin_headers(workshop)
    add_partner(workshop, admin)
    inviter = open_business(workshop, "+995 555 12 34 56")
    invite_code = program(workshop, inviter)["code"]
    open_business(workshop, "+995 555 65 43 21", referral_code="agency-tbilisi")
    open_business(workshop, "+995 555 65 43 22", referral_code="agency-tbilisi")
    open_business(workshop, "+995 555 65 43 23", referral_code=invite_code)

    metrics = workshop.client.get("/v1/admin/metrics", headers=admin)

    assert metrics.status_code == 200, metrics.text
    rows = {
        row["referral_code"]: row["sign_ups"]
        for row in metrics.json()["growth"]["sources"]
    }
    assert rows["agency-tbilisi"] == 2
    assert rows[invite_code] == 1
    assert rows[None] >= 1
