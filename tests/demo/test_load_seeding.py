"""
`workshop seed-load` (in memory): every load business serves the requests
the load tests make, and the manifest names what they need.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.dto.load_data import LoadBusinessSeed, SeedLoadCommand
from app.use_cases.demo.load.prepare_load_businesses_use_case import split_evenly
from tests.e2e.harness import Workshop, bearer, start_workshop

TELEGRAM_UPDATE: dict[str, Any] = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 1_790_000_000,
        "chat": {"id": 4242, "type": "private"},
        "from": {"id": 4242, "first_name": "Nino"},
        "text": "Are you open tonight?",
    },
}


@pytest.fixture(scope="module")
def seeded() -> tuple[Workshop, list[LoadBusinessSeed]]:
    workshop = start_workshop()
    manifest = workshop.container.operators.demo.seed_load_operator().operate(
        SeedLoadCommand.model_validate(
            {
                "business_count": 3,
                "message_count": 1_501,
                "booking_count": 151,
                "visitor_count": 7,
                "random_seed": 11,
            }
        )
    )
    return workshop, manifest.businesses


def test_the_volume_is_split_over_the_businesses(
    seeded: tuple[Workshop, list[LoadBusinessSeed]],
) -> None:
    _, businesses = seeded

    assert [int(entry.message_count) for entry in businesses] == [501, 500, 500]
    assert [int(entry.booking_count) for entry in businesses] == [51, 50, 50]
    assert [len(entry.visitors) for entry in businesses] == [3, 2, 2]
    assert all(len(entry.conversation_ids) == 20 for entry in businesses)
    assert len({str(entry.owner_access_token) for entry in businesses}) == 3


def test_every_measured_request_answers(
    seeded: tuple[Workshop, list[LoadBusinessSeed]],
) -> None:
    workshop, businesses = seeded
    with TestClient(workshop.application) as client:
        for entry in businesses:
            headers = bearer(str(entry.owner_access_token))
            base = f"/v1/businesses/{entry.business_id}"
            feed = client.get(f"{base}/conversations", headers=headers)
            card = client.get(
                f"{base}/conversations/{entry.conversation_ids[0]}", headers=headers
            )
            visitor = entry.visitors[0]
            poll = client.get(
                f"/v1/widget/{entry.business_id}/messages",
                params={"after": str(visitor.latest_message_id)},
                headers={"X-Widget-Session-Key": str(visitor.session_key)},
            )

            assert client.get("/v1/me", headers=headers).status_code == 200
            assert feed.status_code == 200 and len(feed.json()["items"]) == 50
            assert card.status_code == 200 and card.json()["messages"]
            assert client.get(f"{base}/dashboard", headers=headers).status_code == 200
            assert (
                client.get(
                    f"{base}/availability",
                    params={"date": "2026-10-06", "party_size": "2"},
                    headers=headers,
                ).status_code
                == 200
            )
            assert poll.status_code == 200
            assert poll.json()["items"] == []
            assert poll.json()["cursor"] == str(visitor.latest_message_id)


def test_restaurants_take_telegram_webhooks_with_their_secret(
    seeded: tuple[Workshop, list[LoadBusinessSeed]],
) -> None:
    workshop, businesses = seeded
    restaurant, salon = businesses[0], businesses[1]
    path = f"/v1/channels/telegram/{restaurant.telegram_channel_id}/webhook"
    with TestClient(workshop.application) as client:
        accepted = client.post(
            path,
            json=TELEGRAM_UPDATE,
            headers={
                "X-Telegram-Bot-Api-Secret-Token": str(
                    restaurant.telegram_webhook_secret
                )
            },
        )
        refused = client.post(
            path,
            json=TELEGRAM_UPDATE,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        )

    assert accepted.status_code == 200 and accepted.json()["queued"] == 1
    assert refused.status_code == 401
    assert salon.telegram_channel_id is None
    assert salon.telegram_webhook_secret is None


@pytest.mark.parametrize(
    ("total", "parts", "expected"),
    [(10, 3, [4, 3, 3]), (2, 4, [1, 1, 0, 0]), (0, 2, [0, 0])],
)
def test_split_evenly_gives_the_first_parts_the_remainder(
    total: int, parts: int, expected: list[int]
) -> None:
    assert [split_evenly(total, parts, index) for index in range(parts)] == expected
