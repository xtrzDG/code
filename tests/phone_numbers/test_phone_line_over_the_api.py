"""
The phone line over the real application (tests/e2e/harness.py): an owner
finds a number, takes it once however often the cabinet retries, sees it on
the phone card and gives it back by turning the phone channel off; on a
server without a carrier the owner asks the team instead. The carrier and
the voice platform are the fake of `provisioner_fakes.py`; nothing touches
the network.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.containers.app import AppContainer
from app.schemas.dto.jobs import JobTick
from app.schemas.typings.platform.constrained_strings import JobName
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.journeys import sign_in_and_create_restaurant
from tests.e2e.workshop_container import replace_provider
from tests.phone_numbers.provisioner_fakes import (
    AUSTIN_NUMBERS,
    FakePhoneNumberProvisioner,
)

type JsonObject = dict[str, Any]

KEY: str = "5b0f2d7e-9c41-4a3e-8f6d-2e7c1a9b4d30"
OTHER_KEY: str = "8e3c1b6a-0d2f-4c7b-9a5e-6f1d3b8c2a47"


@pytest.fixture
def carrier() -> FakePhoneNumberProvisioner:
    return FakePhoneNumberProvisioner()


@pytest.fixture
def workshop(carrier: FakePhoneNumberProvisioner) -> Iterator[Workshop]:
    def use_the_fake_carrier(container: AppContainer) -> None:
        replace_provider(container.adapters.calls.phone_number_provisioner, carrier)

    workshop = start_workshop(prepare=use_the_fake_carrier)
    with workshop.client:
        yield workshop


@pytest.fixture
def teamless_workshop() -> Iterator[Workshop]:
    """The plain workshop: no carrier keys, so the team arranges numbers."""

    workshop = start_workshop()
    with workshop.client:
        yield workshop


def open_business(workshop: Workshop) -> tuple[str, dict[str, str]]:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    return f"/v1/businesses/{business_id}", bearer(token)


def search_austin(workshop: Workshop, base: str, headers: dict[str, str]) -> JsonObject:
    found = workshop.client.get(
        f"{base}/phone-line/offers",
        params={"country": "us", "number_type": "local", "city": " Austin "},
        headers=headers,
    )
    assert found.status_code == 200, found.text
    offers: JsonObject = found.json()
    return offers


def maintain(workshop: Workshop) -> None:
    operator = workshop.container.operators.calls.maintain_phone_numbers_operator()
    operator.operate(
        JobTick(
            job_name=JobName("maintain_phone_numbers"),
            scheduled_at=workshop.clock.wall_clock.now_unix(),
        )
    )


def test_an_owner_takes_a_number_once_and_gives_it_back(
    workshop: Workshop, carrier: FakePhoneNumberProvisioner
) -> None:
    client = workshop.client
    base, headers = open_business(workshop)

    line = client.get(f"{base}/phone-line", headers=headers).json()
    assert line["are_numbers_self_serve"] is True
    assert "US" in line["self_serve_countries"]
    assert line["default_country_code"] == "GE"
    assert line["rented_number"] is None
    offers = search_austin(workshop, base, headers)
    assert offers["availability"] == "self_serve"
    assert [offer["phone_number"] for offer in offers["offers"]] == list(AUSTIN_NUMBERS)
    price = offers["monthly_price"]["money"]
    assert price["currency_code"] == "GEL"

    body: JsonObject = {
        "phone_number": AUSTIN_NUMBERS[0],
        "number_type": "local",
        "monthly_price": price,
        "locality": "Austin",
    }
    keyed = {**headers, "Idempotency-Key": KEY}
    taken = client.post(f"{base}/phone-line/number", json=body, headers=keyed)
    retried = client.post(f"{base}/phone-line/number", json=body, headers=keyed)

    assert (taken.status_code, retried.status_code) == (201, 201), taken.text
    assert retried.json() == taken.json()
    assert retried.headers["idempotent-replayed"] == "true"
    assert [str(number.phone_number) for number in carrier.bought] == [
        AUSTIN_NUMBERS[0]
    ]
    assert taken.json()["status"] == "active"
    assert taken.json()["locality"] == "Austin"
    card = client.get(f"{base}/phone-line", headers=headers).json()
    assert card["rented_number"]["phone_number"] == AUSTIN_NUMBERS[0]
    channels = client.get(f"{base}/channels", headers=headers).json()
    [phone] = [channel for channel in channels if channel["channel"] == "phone"]
    assert phone["status"] == "connected"

    turned_off = client.delete(f"{base}/channels/phone", headers=headers)

    assert turned_off.status_code == 204, turned_off.text
    releasing = client.get(f"{base}/phone-line", headers=headers).json()
    assert releasing["rented_number"]["status"] == "releasing"
    assert carrier.releases == []
    maintain(workshop)
    assert [str(release.provider_number_id) for release in carrier.releases] == [
        str(carrier.bought[0].provider_number_id)
    ]
    gone = client.get(f"{base}/phone-line", headers=headers).json()
    assert gone["rented_number"] is None


def test_a_changed_price_buys_nothing(
    workshop: Workshop, carrier: FakePhoneNumberProvisioner
) -> None:
    base, headers = open_business(workshop)
    price = search_austin(workshop, base, headers)["monthly_price"]["money"]
    stale = {**price, "amount_minor": int(price["amount_minor"]) - 100}

    refused = workshop.client.post(
        f"{base}/phone-line/number",
        json={
            "phone_number": AUSTIN_NUMBERS[1],
            "number_type": "local",
            "monthly_price": stale,
        },
        headers=headers,
    )

    assert refused.status_code == 409, refused.text
    assert carrier.bought == []


@pytest.mark.parametrize(
    "params",
    [
        {"number_type": "local"},
        {"country": "", "number_type": "local"},
        {"country": "USA", "number_type": "local"},
        {"country": "US", "number_type": "satellite"},
        {"country": "US", "number_type": "local", "city": "x" * 200},
    ],
)
def test_a_search_needs_a_country_and_a_kind_of_number(
    workshop: Workshop, carrier: FakePhoneNumberProvisioner, params: dict[str, str]
) -> None:
    base, headers = open_business(workshop)

    refused = workshop.client.get(
        f"{base}/phone-line/offers", params=params, headers=headers
    )

    assert refused.status_code == 422, refused.text
    assert carrier.searches == []


def test_without_a_carrier_the_owner_asks_the_team_once(
    teamless_workshop: Workshop,
) -> None:
    client = teamless_workshop.client
    base, headers = open_business(teamless_workshop)
    line = client.get(f"{base}/phone-line", headers=headers).json()
    assert line["are_numbers_self_serve"] is False
    offers = client.get(
        f"{base}/phone-line/offers",
        params={"country": "GE", "number_type": "local"},
        headers=headers,
    ).json()
    assert offers["offers"] == []
    assert offers["availability"] != "self_serve"

    body: JsonObject = {"country_code": "GE", "number_type": "local", "city": "Batumi"}
    asked = client.post(
        f"{base}/phone-line/request",
        json=body,
        headers={**headers, "Idempotency-Key": KEY},
    )
    again = client.post(
        f"{base}/phone-line/request",
        json=body,
        headers={**headers, "Idempotency-Key": OTHER_KEY},
    )

    assert (asked.status_code, again.status_code) == (201, 201), asked.text
    assert again.json() == asked.json()
    assert asked.json()["status"] == "open"
    assert asked.json()["city"] == "Batumi"
    card = client.get(f"{base}/phone-line", headers=headers).json()
    assert card["open_request"]["city"] == "Batumi"

    cancelled = client.delete(f"{base}/phone-line/request", headers=headers)

    assert cancelled.status_code == 204, cancelled.text
    after = client.get(f"{base}/phone-line", headers=headers).json()
    assert after["open_request"] is None
