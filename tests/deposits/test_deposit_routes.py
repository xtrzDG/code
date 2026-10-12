"""
The deposit routes over the real application: the owner turns deposits on,
adds a payment page (https only; a page carrying a key is sealed and shown
without it), sets the deposit of a table, and reads an honest report.
"""

from collections.abc import Iterator

import pytest

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.journeys import JsonObject, sign_in_and_create_restaurant


@pytest.fixture
def owner() -> Iterator[tuple[Workshop, str, dict[str, str]]]:
    workshop = start_workshop()
    with workshop.client:
        token, _owner_id, business_id = sign_in_and_create_restaurant(workshop)
        yield workshop, f"/v1/businesses/{business_id}", bearer(token)


def reason_codes(body: JsonObject) -> list[str]:
    return [str(reason["code"]) for reason in body.get("reasons", [])]


def test_deposits_are_off_until_the_owner_turns_them_on(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner

    initial = workshop.client.get(f"{base}/deposit-settings", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["is_enabled"] is False
    assert initial.json()["hold_minutes"] == 60
    assert initial.json()["currency_code"] == "GEL"
    assert initial.json()["currency_digits"] == 2

    saved = workshop.client.put(
        f"{base}/deposit-settings",
        json={"is_enabled": True, "hold_minutes": 30, "refund_cutoff_hours": 48},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["is_enabled"] is True
    assert saved.json()["hold_minutes"] == 30

    too_short = workshop.client.put(
        f"{base}/deposit-settings",
        json={"is_enabled": True, "hold_minutes": 5},
        headers=headers,
    )
    assert too_short.status_code == 422


def test_a_payment_page_must_be_https(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner

    refused = workshop.client.post(
        f"{base}/deposit-settings/payment-links",
        json={
            "label": "Bank",
            "kind": "template",
            "address": "http://pay.example.com/d?sum={amount}",
        },
        headers=headers,
    )

    assert refused.status_code == 422
    assert reason_codes(refused.json()) == ["link_not_https"]


def test_a_page_with_a_key_is_sealed_and_shown_without_it(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner

    added = workshop.client.post(
        f"{base}/deposit-settings/payment-links",
        json={
            "label": "Checkout",
            "kind": "template",
            "address": (
                "https://checkout.example.com/pay?token=test-token-0000"
                "&sum={amount}&ref={reference}"
            ),
        },
        headers=headers,
    )

    assert added.status_code == 201, added.text
    [link] = added.json()["payment_links"]
    assert link["is_sealed"] is True
    assert "test-token-0000" not in added.text
    assert added.json()["default_payment_link_id"] == link["id"]

    removed = workshop.client.delete(
        f"{base}/deposit-settings/payment-links/{link['id']}", headers=headers
    )
    assert removed.status_code == 204
    after = workshop.client.get(f"{base}/deposit-settings", headers=headers).json()
    assert after["payment_links"] == []


def test_turning_deposits_on_keeps_the_default_page(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner
    added = workshop.client.post(
        f"{base}/deposit-settings/payment-links",
        json={
            "label": "Bank",
            "kind": "template",
            "address": "https://pay.example.com/d?sum={amount}&ref={reference}",
        },
        headers=headers,
    )
    assert added.status_code == 201, added.text
    page_id = added.json()["default_payment_link_id"]

    turned_on = workshop.client.put(
        f"{base}/deposit-settings", json={"is_enabled": True}, headers=headers
    )

    assert turned_on.status_code == 200, turned_on.text
    assert turned_on.json()["is_enabled"] is True
    assert turned_on.json()["default_payment_link_id"] == page_id


def test_the_owner_sets_the_deposit_of_a_table(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner
    table = workshop.client.post(
        f"{base}/resources", json={"name": "Terrace", "capacity": 8}, headers=headers
    )
    assert table.status_code == 201, table.text
    resource_id = table.json()["id"]

    saved = workshop.client.put(
        f"{base}/deposit-settings/policies",
        json={
            "target": "resource",
            "resource_id": resource_id,
            "policy": {"rule": "per_guest", "amount_minor": 2000, "min_party_size": 6},
        },
        headers=headers,
    )

    assert saved.status_code == 200, saved.text
    [policy] = saved.json()["policies"]
    assert policy["resource_id"] == resource_id
    assert policy["rule"] == "per_guest"
    assert policy["amount_minor"] == 2000
    assert policy["currency_code"] == "GEL"

    cleared = workshop.client.put(
        f"{base}/deposit-settings/policies",
        json={"target": "resource", "resource_id": resource_id, "policy": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["policies"] == []


def test_a_policy_names_what_its_rule_needs(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner

    no_amount = workshop.client.put(
        f"{base}/deposit-settings/policies",
        json={"target": "banquet", "policy": {"rule": "fixed"}},
        headers=headers,
    )
    unknown_table = workshop.client.put(
        f"{base}/deposit-settings/policies",
        json={
            "target": "resource",
            "resource_id": "resource_00000000-0000-4000-8000-000000000000",
            "policy": {"rule": "fixed", "amount_minor": 5000},
        },
        headers=headers,
    )

    assert no_amount.status_code == 422
    assert unknown_table.status_code in (404, 422)


def test_the_report_says_when_there_is_not_enough_data(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner

    report = workshop.client.get(
        f"{base}/deposit-report", params={"days": 30}, headers=headers
    )

    assert report.status_code == 200, report.text
    body = report.json()
    assert body["requested_count"] == 0
    assert body["with_deposit"]["has_enough_data"] is False
    assert body["with_deposit"]["no_show_percent"] is None
    assert body["without_deposit"]["has_enough_data"] is False
    assert body["min_sample"] == 20


def test_an_unknown_deposit_is_not_found(
    owner: tuple[Workshop, str, dict[str, str]],
) -> None:
    workshop, base, headers = owner
    unknown = "deposit_request_00000000-0000-4000-8000-000000000000"

    read = workshop.client.get(f"{base}/deposits/{unknown}", headers=headers)
    paid = workshop.client.post(f"{base}/deposits/{unknown}/paid", headers=headers)

    assert read.status_code == 404
    assert paid.status_code == 404
