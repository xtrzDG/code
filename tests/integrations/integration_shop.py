"""
A restaurant with one table, through the real application, for the
integrations: its owner's cabinet calls, the webhook receivers as a fake,
the API keys it makes and the public API called with them.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

from fastapi.testclient import TestClient
from httpx2 import Response

from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import sign_in_and_create_restaurant
from tests.integrations.fake_webhook_poster import FakeWebhookPoster

type JsonObject = dict[str, Any]

DAY: str = "2026-10-06"
RECEIVER_URL: str = "https://hooks.example.com/workshop"
OPEN_ALL_WEEK: list[JsonObject] = [
    {"weekday": weekday, "opens_at": 720, "closes_at": 1020} for weekday in range(1, 8)
]
ALL_SCOPES: list[str] = [
    "bookings:read",
    "bookings:write",
    "leads:read",
    "leads:write",
    "contacts:read",
    "conversations:read",
    "webhooks:manage",
]


@dataclass
class IntegrationShop:
    workshop: Workshop
    token: str
    business_id: str
    resource_id: str

    @property
    def client(self) -> TestClient:
        return self.workshop.client

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.token)

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"

    @property
    def receivers(self) -> FakeWebhookPoster:
        return cast(FakeWebhookPoster, self.workshop.container.clients.webhook_poster())

    def get(self, path: str, **params: str) -> Response:
        return self.client.get(path, params=params, headers=self.headers)

    def post(self, path: str, body: JsonObject | None = None) -> Response:
        return self.client.post(path, json=body or {}, headers=self.headers)

    def patch(self, path: str, body: JsonObject) -> Response:
        return self.client.patch(path, json=body, headers=self.headers)

    def delete(self, path: str) -> Response:
        return self.client.delete(path, headers=self.headers)

    def add_webhook(
        self, events: list[str] | None = None, url: str = RECEIVER_URL
    ) -> JsonObject:
        created = self.post(
            f"{self.base}/webhooks",
            {"url": url, "label": "CRM", "event_types": events or ["booking.created"]},
        )
        assert created.status_code == 201, created.text
        return dict(created.json())

    def book(self, time: str = "13:00", name: str = "Nino") -> JsonObject:
        booked = self.post(
            f"{self.base}/bookings",
            {
                "contact_name": name,
                "contact_phone_number": "+995 555 11 22 33",
                "date": DAY,
                "time": time,
                "party_size": 2,
                "resource_id": self.resource_id,
            },
        )
        assert booked.status_code == 201, booked.text
        return dict(booked.json()["booking"])

    def deliveries(self, webhook_id: str) -> list[JsonObject]:
        log = self.get(f"{self.base}/webhooks/{webhook_id}/deliveries")
        assert log.status_code == 200, log.text
        return list(log.json()["items"])

    def run_jobs(self) -> None:
        self.workshop.run_queued_jobs()

    def add_api_key(self, scopes: list[str] | None = None, name: str = "Zapier") -> str:
        created = self.post(
            f"{self.base}/api-keys", {"name": name, "scopes": scopes or ALL_SCOPES}
        )
        assert created.status_code == 201, created.text
        return str(created.json()["token"])

    def api(
        self,
        method: str,
        path: str,
        key: str,
        body: JsonObject | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Response:
        return self.client.request(
            method,
            f"/v1/public-api{path}",
            json=body,
            headers={**bearer(key), **(headers or {})},
        )


@contextmanager
def open_integration_shop(
    environment: Mapping[str, str] | None = None,
) -> Generator[IntegrationShop]:
    workshop = start_workshop({**E2E_ENVIRONMENT, **(environment or {})})
    with workshop.client:
        yield open_restaurant(workshop)


def open_restaurant(workshop: Workshop) -> IntegrationShop:
    token, _, business_id = sign_in_and_create_restaurant(workshop)
    table = workshop.client.post(
        f"/v1/businesses/{business_id}/resources",
        json={
            "name": "Window table",
            "capacity": 4,
            "slot_minutes": 60,
            "schedule": OPEN_ALL_WEEK,
        },
        headers=bearer(token),
    )
    assert table.status_code == 201, table.text
    return IntegrationShop(
        workshop=workshop,
        token=token,
        business_id=business_id,
        resource_id=str(table.json()["id"]),
    )


OTHER_OWNER_PHONE: str = "+995 555 98 76 54"


def open_other_business(workshop: Workshop) -> IntegrationShop:
    """A second restaurant of another owner in the same application."""

    token, _ = workshop.sign_in_with_phone(OTHER_OWNER_PHONE)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": "Shavi Lomi", "niche_key": "restaurant"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    business_id = str(created.json()["id"])
    table = workshop.client.post(
        f"/v1/businesses/{business_id}/resources",
        json={
            "name": "Bar",
            "capacity": 2,
            "slot_minutes": 60,
            "schedule": OPEN_ALL_WEEK,
        },
        headers=bearer(token),
    )
    assert table.status_code == 201, table.text
    return IntegrationShop(
        workshop=workshop,
        token=token,
        business_id=business_id,
        resource_id=str(table.json()["id"]),
    )
