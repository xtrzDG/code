"""
A closing business connects no channel by any path until its closure is
cancelled: no Facebook sign-in starts or finishes (WhatsApp Embedded Signup,
the page picker of Messenger and Instagram), and no phone number is rented,
so the carrier sells none and no rental month is billed.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.containers.app import AppContainer
from tests.business_closures.closure_world import open_closure_world
from tests.business_closures.test_closing_stays_closed import assert_still_closing
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.journeys import sign_in_and_create_restaurant
from tests.e2e.workshop_container import replace_provider
from tests.phone_numbers.provisioner_fakes import (
    AUSTIN_NUMBERS,
    FakePhoneNumberProvisioner,
)

# Well-formed sign-in values: the refusal comes before they are looked at.
STATE: str = "q3Jx8m1lV0k7yZcT2b9WnHf4sR6uPaEoLdIgKjQwXeM"
CODE: str = "AQBx-signup-code"
PAGE_ID: str = "104857600123456"
RESTAURANT: str = "Salobie Bia"


def assert_refused_as_closing(response: Any) -> None:
    assert response.status_code == 409, response.text
    assert "closing" in response.json()["message"]


def test_no_facebook_sign_in_connects_a_closing_business() -> None:
    with open_closure_world() as world:
        world.close_b()
        channels = f"/v1/businesses/{world.business_b}/channels"
        client = world.workshop.client

        started = client.post(
            f"{channels}/meta/sign-in",
            json={"purpose": "whatsapp"},
            headers=world.owner_b,
        )
        signed_up = client.post(
            f"{channels}/whatsapp/embedded-signup",
            json={"state": STATE, "code": CODE},
            headers=world.owner_b,
        )
        picked = client.put(
            f"{channels}/messenger/page",
            json={"state": STATE, "page_id": PAGE_ID},
            headers=world.owner_b,
        )

        for response in (started, signed_up, picked):
            assert_refused_as_closing(response)
        assert_still_closing(world)


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


def test_a_closing_business_rents_no_number(
    workshop: Workshop, carrier: FakePhoneNumberProvisioner
) -> None:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    base, headers = f"/v1/businesses/{business_id}", bearer(token)
    client = workshop.client
    found = client.get(
        f"{base}/phone-line/offers",
        params={"country": "us", "number_type": "local", "city": "Austin"},
        headers=headers,
    )
    assert found.status_code == 200, found.text
    offers = found.json()
    closed = client.post(
        f"{base}/closure", json={"confirmation_name": RESTAURANT}, headers=headers
    )
    assert closed.status_code == 200, closed.text

    rented = client.post(
        f"{base}/phone-line/number",
        json={
            "phone_number": AUSTIN_NUMBERS[0],
            "number_type": "local",
            "offer_token": offers["offers"][0]["offer_token"],
            "monthly_price": offers["monthly_price"]["money"],
        },
        headers={**headers, "Idempotency-Key": "0c6f3e2a-7d14-4b9e-a8c5-3f2e1d0b9a87"},
    )

    assert_refused_as_closing(rented)
    assert carrier.bought == []
    line = client.get(f"{base}/phone-line", headers=headers).json()
    assert line["rented_number"] is None
