"""A workshop API with a restaurant, its staff contacts and a fake push service."""

import base64
import os
from dataclasses import dataclass
from typing import cast

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from dependency_injector import providers

from app.containers.app import AppContainer
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import CABINET_ORIGIN, E2E_ENVIRONMENT, JsonObject
from tests.e2e.journeys import sign_in_and_create_restaurant
from tests.e2e.workshop_container import OverridableProvider
from tests.notifications.web_push_fakes import FakeWebPushClient

NOTIFICATIONS_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "CABINET_BASE_URL": CABINET_ORIGIN,
}
FCM_ENDPOINT: str = "https://fcm.googleapis.com/fcm/send/device-token-1"
STAFF_CONTACTS: list[JsonObject] = [
    {"name": "Nino", "channel": "telegram", "address": "70001", "language": "ka"},
    {
        "name": "Anna",
        "channel": "email",
        "address": "anna@salobie.example",
        "language": "en",
    },
    {"name": "Gio", "channel": "sms", "address": "+995555000222", "language": "ru"},
    {
        "name": "Levan",
        "channel": "whatsapp",
        "address": "+995555000333",
        "language": "ka",
    },
]


@dataclass(frozen=True)
class Restaurant:
    """A restaurant's owner session over a started workshop."""

    workshop: Workshop
    token: str
    owner_id: str
    business_id: str

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business_id}"

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.token)


def start_notifications_workshop(push: FakeWebPushClient | None) -> Workshop:
    """The workshop API; device notifications are on when `push` is given."""

    def prepare(container: AppContainer) -> None:
        if push is not None:
            cast(OverridableProvider, container.clients.web_push_client).override(
                providers.Object(push)
            )

    return start_workshop(NOTIFICATIONS_ENVIRONMENT, prepare)


def open_restaurant_with_contacts(workshop: Workshop) -> Restaurant:
    token, owner_id, business_id = sign_in_and_create_restaurant(workshop)
    restaurant = Restaurant(workshop, token, owner_id, business_id)
    saved = workshop.client.patch(
        restaurant.base,
        json={"manager_contacts": STAFF_CONTACTS},
        headers=restaurant.headers,
    )
    assert saved.status_code == 200, saved.text
    return restaurant


def contacts_by_name(restaurant: Restaurant) -> dict[str, JsonObject]:
    listed = restaurant.workshop.client.get(
        f"{restaurant.base}/notification-contacts", headers=restaurant.headers
    )
    assert listed.status_code == 200, listed.text
    return {str(item["name"]): item for item in listed.json()["items"]}


def browser_subscription(endpoint: str = FCM_ENDPOINT) -> JsonObject:
    """What PushSubscription.toJSON() gives, with real keys."""

    public_key = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    )
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": encode(public_key), "auth": encode(os.urandom(16))},
        "language": "ru",
    }


def encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
