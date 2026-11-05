"""
Bookings → Waitlist and Bookings → Return visits over HTTP on the demo
restaurant, and the value lines they bring (owner-only refusals are in the
authorization matrix).
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

import pytest

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.platform.authorization_world import (
    DEMO_OWNER_EMAIL,
    DEMO_RESTAURANT,
    DEMO_STAFF_PHONE,
)

type JsonObject = dict[str, Any]


@dataclass(frozen=True)
class DemoRestaurant:
    workshop: Workshop
    base: str
    owner: dict[str, str]
    staff: dict[str, str]

    def get(self, path: str, headers: dict[str, str] | None = None) -> Any:
        response = self.workshop.client.get(
            f"{self.base}{path}", headers=headers or self.owner
        )
        assert response.status_code == 200, response.text
        return response.json()


@pytest.fixture(scope="module")
def demo() -> Iterator[DemoRestaurant]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "SEED_DEMO_DATA": "true"})
    with workshop.client:
        owner = bearer(workshop.sign_in_with_email(DEMO_OWNER_EMAIL)[0])
        staff = bearer(workshop.sign_in_with_phone(DEMO_STAFF_PHONE)[0])
        businesses = cast(
            list[JsonObject],
            workshop.client.get("/v1/businesses", headers=owner).json(),
        )
        business = next(item for item in businesses if item["name"] == DEMO_RESTAURANT)
        yield DemoRestaurant(
            workshop=workshop,
            base=f"/v1/businesses/{business['id']}",
            owner=owner,
            staff=staff,
        )


def test_staff_see_who_waits_first_come_first(demo: DemoRestaurant) -> None:
    page = demo.get("/waitlist", headers=demo.staff)

    waiting = cast(list[JsonObject], page["items"])
    assert len(waiting) == 3
    assert [row["status"] for row in waiting] == ["waiting"] * 3
    created = [int(row["created_at"]) for row in waiting]
    assert created == sorted(created)
    assert all(row["contact_name"] for row in waiting)


def test_the_booked_and_the_ended_lists(demo: DemoRestaurant) -> None:
    booked = demo.get("/waitlist?filter=booked")["items"]
    ended = demo.get("/waitlist?filter=ended")["items"]

    assert [row["status"] for row in booked] == ["booked"]
    assert booked[0]["booking_id"] is not None
    assert [row["end_reason"] for row in ended] == ["no_answer"]


def test_an_unknown_filter_is_refused(demo: DemoRestaurant) -> None:
    response = demo.workshop.client.get(
        f"{demo.base}/waitlist?filter=everything", headers=demo.owner
    )

    assert response.status_code in (400, 422)


def test_staff_take_a_guest_off_the_list(demo: DemoRestaurant) -> None:
    before = demo.get("/waitlist")["items"]
    removed = before[-1]

    response = demo.workshop.client.delete(
        f"{demo.base}/waitlist/{removed['id']}", headers=demo.staff
    )

    assert response.status_code == 204
    after = [row["id"] for row in demo.get("/waitlist")["items"]]
    assert removed["id"] not in after
    ended = demo.get("/waitlist?filter=ended")["items"]
    assert removed["id"] in [row["id"] for row in ended]


def test_the_owner_sets_the_hold_within_its_range(demo: DemoRestaurant) -> None:
    client = demo.workshop.client
    path = f"{demo.base}/waitlist-settings"

    assert demo.get("/waitlist-settings")["hold_minutes"] == 30
    too_short = client.put(path, json={"hold_minutes": 10}, headers=demo.owner)
    saved = client.put(
        path, json={"is_enabled": True, "hold_minutes": 45}, headers=demo.owner
    )

    assert too_short.status_code in (400, 422)
    assert saved.status_code == 200, saved.text
    assert saved.json()["hold_minutes"] == 45


def test_return_visits_start_from_the_niche_rule(demo: DemoRestaurant) -> None:
    settings = demo.get("/campaign-settings", headers=demo.staff)

    assert settings["is_enabled"] is True
    assert (settings["rule_kind"], settings["delay_days"]) == ("rebook", 30)
    assert (settings["niche_rule_kind"], settings["niche_delay_days"]) == (
        "rebook",
        30,
    )
    assert {preview["language"] for preview in settings["previews"]} == {
        "ka",
        "ru",
        "en",
    }


def test_a_segment_audience_needs_a_segment_of_the_business(
    demo: DemoRestaurant,
) -> None:
    response = demo.workshop.client.put(
        f"{demo.base}/campaign-settings",
        json={
            "is_enabled": True,
            "rule_kind": "rebook",
            "delay_days": 35,
            "audience": "segment",
        },
        headers=demo.owner,
    )

    assert response.status_code in (400, 422)


def test_the_owner_sees_whom_the_campaign_wrote_to(demo: DemoRestaurant) -> None:
    messages = cast(list[JsonObject], demo.get("/campaign-messages")["items"])

    statuses = {row["status"] for row in messages}
    assert "booked" in statuses
    assert all(row["contact_id"] for row in messages)


def test_the_value_counts_the_waitlist_and_the_campaigns_apart(
    demo: DemoRestaurant,
) -> None:
    value = demo.get("/value?period=30d")

    current = value["current"]
    assert current["waitlist_booking_count"] >= 1
    assert current["campaign_booking_count"] >= 1
