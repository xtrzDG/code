"""
Rotating the encryption key end to end: a new key goes first in
ENCRYPTION_KEYS, the platform admin starts the re-encryption, the worker
moves every stored secret to the new key and registers Telegram webhooks
again; afterwards the old key can be dropped.
"""

from collections.abc import Iterator

import pytest

from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import BUSINESS_BOT_TOKEN, sign_in_and_create_restaurant
from tests.e2e.key_rotation_world import (
    ACCESS_TOKEN,
    NEW_KEY,
    OLD_KEY,
    REFRESH_TOKEN,
    ROTATING_ENVIRONMENT,
    seal_with_old_key,
    store_old_secrets,
    stored_secrets_open_with_the_new_key_alone,
)

KEYS_URL: str = "/v1/admin/security/encryption-keys"


@pytest.fixture
def rotating() -> Iterator[Workshop]:
    workshop = start_workshop(ROTATING_ENVIRONMENT)
    with workshop.client:
        yield workshop


def connect_telegram(workshop: Workshop, business_id: str, token: str) -> str:
    connected = workshop.client.put(
        f"/v1/businesses/{business_id}/channels/telegram",
        json={"bot_token": BUSINESS_BOT_TOKEN},
        headers=bearer(token),
    )
    assert connected.status_code == 200, connected.text
    return str(connected.json()["id"])


def webhook_secret(key: str) -> str:
    return str(
        derive_telegram_webhook_secret(
            PlatformSecret(key), ChannelSecret(BUSINESS_BOT_TOKEN)
        )
    )


def test_the_admin_rotates_every_secret_to_the_new_key(rotating: Workshop) -> None:
    owner_token, owner_id, business_id = sign_in_and_create_restaurant(rotating)
    channel_id = connect_telegram(rotating, business_id, owner_token)
    seal_with_old_key(rotating, channel_id)
    store_old_secrets(rotating, business_id, owner_id)
    admin_token, _ = rotating.sign_in_with_email(ADMIN_EMAIL)
    admin = bearer(admin_token)
    webhook = f"/v1/channels/telegram/{channel_id}/webhook"
    update = {"update_id": 5, "message": {"message_id": 1, "chat": {"id": 7}}}

    # Before the run, a webhook registered with the old key's secret works.
    old_signed = rotating.client.post(
        webhook,
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret(OLD_KEY)},
    )
    before = rotating.client.get(KEYS_URL, headers=admin)
    started = rotating.client.post(f"{KEYS_URL}/rotate", headers=admin)
    while_running = rotating.client.post(f"{KEYS_URL}/rotate", headers=admin)
    owner_denied = rotating.client.post(
        f"{KEYS_URL}/rotate", headers=bearer(owner_token)
    )
    rotating.telegram.requests.clear()
    rotating.run_queued_jobs()
    after = rotating.client.get(KEYS_URL, headers=admin)

    assert old_signed.status_code == 200, old_signed.text
    assert before.json() == {"key_count": 2, "latest_rotation": None}
    assert started.status_code == 202, started.text
    assert started.json()["rotation"]["status"] == "queued"
    assert while_running.status_code == 409
    assert owner_denied.status_code == 403
    rotation = after.json()["latest_rotation"]
    assert rotation["status"] == "done", rotation
    assert {
        name: rotation[name]
        for name in (
            "key_count",
            "secrets_total",
            "secrets_rotated",
            "secrets_current",
            "secrets_unreadable",
            "webhooks_renewed",
            "webhooks_failed",
        )
    } == {
        # The admin's authenticator secret, sealed at sign-in with the new
        # key, is already current.
        "key_count": 2,
        "secrets_total": 5,
        "secrets_rotated": 3,
        "secrets_current": 1,
        "secrets_unreadable": 1,
        "webhooks_renewed": 1,
        "webhooks_failed": 0,
    }
    [registered] = rotating.telegram.bodies("/setWebhook")
    assert registered["secret_token"] == webhook_secret(NEW_KEY)
    assert registered["url"].endswith(webhook)
    assert stored_secrets_open_with_the_new_key_alone(rotating, business_id) == [
        REFRESH_TOKEN,
        ACCESS_TOKEN,
        ChannelSecret(BUSINESS_BOT_TOKEN),
    ]


def test_a_second_run_finds_everything_current(rotating: Workshop) -> None:
    owner_token, _, business_id = sign_in_and_create_restaurant(rotating)
    connect_telegram(rotating, business_id, owner_token)
    admin = bearer(rotating.sign_in_with_email(ADMIN_EMAIL)[0])

    for _ in range(2):
        assert (
            rotating.client.post(f"{KEYS_URL}/rotate", headers=admin).status_code == 202
        )
        rotating.run_queued_jobs()

    rotation = rotating.client.get(KEYS_URL, headers=admin).json()["latest_rotation"]
    assert (
        rotation["status"],
        rotation["secrets_current"],
        rotation["secrets_rotated"],
    ) == (
        "done",
        2,  # the bot token and the admin's authenticator secret
        0,
    )
