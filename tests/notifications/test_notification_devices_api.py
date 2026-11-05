"""Settings → Notifications over HTTP: my events, quiet hours and devices."""

import json

from app.schemas.exceptions.notification_errors import PushSubscriptionGoneError
from tests.e2e.harness import bearer
from tests.e2e.harness_settings import CABINET_ORIGIN, JsonObject
from tests.notifications.notification_api_world import (
    Restaurant,
    browser_subscription,
    open_restaurant_with_contacts,
    start_notifications_workshop,
)
from tests.notifications.web_push_fakes import FAKE_VAPID_PUBLIC_KEY, FakeWebPushClient


def preferences_path(restaurant: Restaurant) -> str:
    return f"{restaurant.base}/notification-preferences"


def devices_path(restaurant: Restaurant) -> str:
    return f"{restaurant.base}/push-subscriptions"


def test_i_choose_my_events_and_quiet_hours() -> None:
    workshop = start_notifications_workshop(push=FakeWebPushClient())
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        client, path = workshop.client, preferences_path(restaurant)

        mine = client.get(path, headers=restaurant.headers)
        assert mine.status_code == 200, mine.text
        assert mine.json() == {
            "business_id": restaurant.business_id,
            "preferences": {
                "events": ["handoff", "lead", "booking"],
                "quiet_hours": None,
            },
            "push_public_key": str(FAKE_VAPID_PUBLIC_KEY),
            "devices": [],
        }

        chosen = {
            "events": ["handoff"],
            "quiet_hours": {"starts_at": "22:00", "ends_at": "08:00"},
        }
        saved = client.put(path, json=chosen, headers=restaurant.headers)
        assert saved.status_code == 200, saved.text
        assert saved.json()["preferences"] == chosen
        assert client.get(path, headers=restaurant.headers).json()["preferences"] == (
            chosen
        )

        invalid_bodies: list[JsonObject] = [
            {"events": ["handoff"], "quiet_hours": {"starts_at": "22:00"}},
            {
                "events": [],
                "quiet_hours": {"starts_at": "09:00", "ends_at": "09:00"},
            },
            {"events": ["birthday"]},
        ]
        for invalid in invalid_bodies:
            refused = client.put(path, json=invalid, headers=restaurant.headers)
            assert refused.status_code == 422, (invalid, refused.text)

        # Preferences are each member's own: another user has no access.
        other_token, _ = workshop.sign_in_with_email("giulia@trattoria.example")
        assert client.get(path, headers=bearer(other_token)).status_code == 404


def test_this_device_is_turned_on_checked_and_turned_off() -> None:
    push = FakeWebPushClient()
    workshop = start_notifications_workshop(push=push)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        client, path = workshop.client, devices_path(restaurant)
        subscription = browser_subscription()

        created = client.post(path, json=subscription, headers=restaurant.headers)
        assert created.status_code == 201, created.text
        device_id = str(created.json()["id"])
        assert created.json()["language"] == "ru"
        again = client.post(
            path,
            json={**subscription, "language": "ka"},
            headers=restaurant.headers,
        )
        assert again.json()["id"] == device_id
        settings = client.get(preferences_path(restaurant), headers=restaurant.headers)
        assert [device["id"] for device in settings.json()["devices"]] == [device_id]

        checked = client.post(f"{path}/{device_id}/test", headers=restaurant.headers)
        assert checked.status_code == 200, checked.text
        assert checked.json()["delivery"]["status"] == "delivered"
        [sent] = push.sent
        payload = json.loads(str(sent.payload))
        assert payload["tag"] == "check:notifications"
        assert str(payload["url"]).startswith(f"{CABINET_ORIGIN}/n/")
        assert "+995" not in str(sent.payload)
        [device] = client.get(
            preferences_path(restaurant), headers=restaurant.headers
        ).json()["devices"]
        assert device["delivered_at"] is not None and device["language"] == "ka"

        # Another member cannot touch my device.
        other_token, _ = workshop.sign_in_with_email("giulia@trattoria.example")
        assert (
            client.delete(f"{path}/{device_id}", headers=bearer(other_token))
        ).status_code == 404

        removed = client.delete(f"{path}/{device_id}", headers=restaurant.headers)
        assert removed.status_code == 204
        assert (
            client.delete(f"{path}/{device_id}", headers=restaurant.headers)
        ).status_code == 404


def test_a_device_the_push_service_forgot_disappears_after_its_check() -> None:
    push = FakeWebPushClient(PushSubscriptionGoneError("gone (HTTP 410)"))
    workshop = start_notifications_workshop(push=push)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        client, path = workshop.client, devices_path(restaurant)
        created = client.post(
            path, json=browser_subscription(), headers=restaurant.headers
        )
        device_id = str(created.json()["id"])

        checked = client.post(f"{path}/{device_id}/test", headers=restaurant.headers)

        assert checked.status_code == 200, checked.text
        assert checked.json()["delivery"]["status"] == "dead"
        settings = client.get(preferences_path(restaurant), headers=restaurant.headers)
        assert settings.json()["devices"] == []


def test_only_real_subscriptions_of_known_push_services_are_accepted() -> None:
    workshop = start_notifications_workshop(push=FakeWebPushClient())
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)
        client, path = workshop.client, devices_path(restaurant)
        foreign = browser_subscription("https://push.attacker.example/endpoint")
        broken = browser_subscription()
        broken["keys"] = {"p256dh": "B" * 87, "auth": "A" * 22}

        for invalid in (foreign, broken, {"endpoint": "https://fcm.googleapis.com"}):
            refused = client.post(path, json=invalid, headers=restaurant.headers)
            assert refused.status_code == 422, (invalid, refused.text)

        # Outside production a local test push service is accepted.
        local = browser_subscription("http://127.0.0.1:9999/push/device")
        accepted = client.post(path, json=local, headers=restaurant.headers)
        assert accepted.status_code == 201, accepted.text


def test_devices_cannot_be_turned_on_while_push_is_not_set_up() -> None:
    workshop = start_notifications_workshop(push=None)
    with workshop.client:
        restaurant = open_restaurant_with_contacts(workshop)

        settings = workshop.client.get(
            preferences_path(restaurant), headers=restaurant.headers
        )
        refused = workshop.client.post(
            devices_path(restaurant),
            json=browser_subscription(),
            headers=restaurant.headers,
        )

        assert settings.json()["push_public_key"] is None
        assert refused.status_code == 409, refused.text
