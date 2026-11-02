"""
The admin's money actions take an Idempotency-Key: a retried credit grant
(a double click, a dropped answer) credits once and answers the first
answer again; the same key with another amount is refused.
"""

from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import sign_in_and_create_restaurant, start_trial_and_accept_dpa

KEY: str = "5d1c9b2e-7f3a-4c8d-9e0b-1a2f3c4d5e6f"
REASON: str = "Goodwill credit after the outage of 2 November"


def test_a_retried_credit_grant_credits_once(workshop: Workshop) -> None:
    owner, _, business_id = sign_in_and_create_restaurant(workshop)
    start_trial_and_accept_dpa(workshop, f"/v1/businesses/{business_id}", bearer(owner))
    admin, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    headers = {**bearer(admin), "Idempotency-Key": KEY}
    url = f"/v1/admin/clients/{business_id}/credits"
    body = {"amount_minor": 2500, "reason": REASON}

    first = workshop.client.post(url, json=body, headers=headers)
    retry = workshop.client.post(url, json=body, headers=headers)
    reused = workshop.client.post(
        url, json={**body, "amount_minor": 9900}, headers=headers
    )
    detail = workshop.client.get(
        f"/v1/admin/clients/{business_id}", headers=bearer(admin)
    )

    assert first.status_code == 200, first.text
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert retry.headers["idempotent-replayed"] == "true"
    assert reused.status_code == 409
    assert reused.json()["reasons"][0]["code"] == "idempotency_key_reused"
    assert detail.json()["account"]["credit_balance"]["amount_minor"] == 2500
