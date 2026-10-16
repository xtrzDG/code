"""
The admin that acts over the real API: a SUPER admin grants credit, gives a
discount and extends the trial (each in the client's audit log and its
timeline), keeps notes; an owner gets 403 and a short reason 422.
"""

from typing import Any

from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import sign_in_and_create_restaurant, start_trial_and_accept_dpa

REASON: str = "Slow onboarding: menu photos arrive next week"


def client_url(business_id: str, path: str = "") -> str:
    return f"/v1/admin/clients/{business_id}{path}"


def test_a_super_admin_acts_on_a_client_and_reads_its_story(
    workshop: Workshop,
) -> None:
    owner, _, business_id = sign_in_and_create_restaurant(workshop)
    start_trial_and_accept_dpa(workshop, f"/v1/businesses/{business_id}", bearer(owner))
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    headers = bearer(admin)
    post = workshop.client.post

    credited = post(
        client_url(business_id, "/credits"),
        json={"amount_minor": 10000, "reason": REASON},
        headers=headers,
    )
    discounted = post(
        client_url(business_id, "/discount"),
        json={"percent": 20, "last_day": "2027-06-30", "reason": REASON},
        headers=headers,
    )
    extended = post(
        client_url(business_id, "/trial-extension"),
        json={"days": 7, "reason": REASON},
        headers=headers,
    )
    detail = workshop.client.get(client_url(business_id), headers=headers)
    story = workshop.client.get(client_url(business_id, "/timeline"), headers=headers)

    assert credited.status_code == 200, credited.text
    assert credited.json()["action"] == "admin_credit_granted"
    assert discounted.status_code == 200, discounted.text
    assert extended.status_code == 200, extended.text
    account: dict[str, Any] = detail.json()["account"]
    assert account["credit_balance"]["amount_minor"] == 10000
    assert account["discount"]["percent"] == 20
    assert detail.json()["summary"]["setup_option"] == "self_serve"
    assert story.status_code == 200, story.text
    actions = [line["audit_action"] for line in story.json()["items"]]
    assert actions[:3] == [
        "admin_trial_extended",
        "admin_discount_given",
        "admin_credit_granted",
    ]
    assert {line["reason"] for line in story.json()["items"][:3]} == {REASON}


def test_notes_are_written_pinned_and_deleted(workshop: Workshop) -> None:
    _, _, business_id = sign_in_and_create_restaurant(workshop)
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    headers = bearer(admin)
    url = client_url(business_id, "/notes")

    created = workshop.client.post(
        url, json={"text": "Call after 18:00"}, headers=headers
    )
    note_id = created.json()["items"][0]["id"]
    pinned = workshop.client.patch(
        f"{url}/{note_id}", json={"is_pinned": True}, headers=headers
    )
    deleted = workshop.client.delete(f"{url}/{note_id}", headers=headers)
    listed = workshop.client.get(url, headers=headers)

    assert created.status_code == 201, created.text
    assert pinned.json()["items"][0]["is_pinned"] is True
    assert deleted.status_code == 204
    assert listed.json() == {"items": []}


def test_owners_are_refused_and_bad_bodies_are_422(workshop: Workshop) -> None:
    owner, _, business_id = sign_in_and_create_restaurant(workshop)
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)

    by_owner = workshop.client.post(
        client_url(business_id, "/credits"),
        json={"amount_minor": 100, "reason": REASON},
        headers=bearer(owner),
    )
    short_reason = workshop.client.post(
        client_url(business_id, "/credits"),
        json={"amount_minor": 100, "reason": "why"},
        headers=bearer(admin),
    )
    no_subscription = workshop.client.post(
        client_url(business_id, "/credits"),
        json={"amount_minor": 100, "reason": REASON},
        headers=bearer(admin),
    )
    unknown_invoice = workshop.client.post(
        client_url(business_id, "/invoices/invoice_bad/manual-payment"),
        json={"method": "cash", "reference": "R-1", "reason": REASON},
        headers=bearer(admin),
    )

    assert by_owner.status_code == 403
    assert short_reason.status_code == 422
    assert no_subscription.status_code == 404
    assert unknown_invoice.status_code == 404
