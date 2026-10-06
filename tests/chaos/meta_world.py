"""
The Meta game day's restaurant: the e2e restaurant with a connected
WhatsApp number (its token sealed with the world's key, as connecting it
stores it), customers who write through Meta's signed webhook, and the
outbox rows of the replies, read straight from the database.
"""

import json
import time
from dataclasses import dataclass

import httpx

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.utilities.channels.channel_endpoints import META_SIGNATURE_HEADER
from tests.channels.channels_payloads import sign_meta
from tests.channels.meta_payloads import (
    PHONE_NUMBER_ID,
    whatsapp_message,
    whatsapp_webhook,
)
from tests.chaos.chaos_world import ChaosWorld
from tests.e2e.harness import bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import open_restaurant
from tests.storage.two_process_world import SeededRestaurant, use_the_real_clock

WHATSAPP_TOKEN: ChannelSecret = ChannelSecret("EAAG-chaos-whatsapp-0000")


def seed_whatsapp_restaurant(database_url: str) -> SeededRestaurant:
    """Open the e2e restaurant and connect its WhatsApp number."""

    workshop = start_workshop(
        {**E2E_ENVIRONMENT, "DATABASE_URL": database_url},
        prepare=use_the_real_clock,
    )
    container = workshop.container
    # While the workshop runs: its lifespan closes the database pool.
    with workshop.client, container.utilities.storage_scope().platform_wide():
        restaurant = open_restaurant(workshop)
        now = container.time_provider.microsecond_wall_clock().now_unix()
        container.repositories.channel_repo().save(
            ChannelDocument(
                business_id=BusinessId(restaurant.business_id),
                kind=ChannelKind.WHATSAPP,
                external_id=ChannelExternalId(PHONE_NUMBER_ID),
                encrypted_secret=container.adapters.secret_cipher().encrypt(
                    WHATSAPP_TOKEN
                ),
                status=ChannelStatus.CONNECTED,
                created_at=now,
                updated_at=now,
            )
        )
    return SeededRestaurant(
        business_id=restaurant.business_id,
        headers=bearer(restaurant.owner_token),
    )


def customer_writes(world: ChaosWorld, api_url: str, index: int, text: str) -> None:
    """Customer `index` writes on WhatsApp (Meta's signed webhook)."""

    sender = f"9955550{index:05d}"
    body = json.dumps(
        whatsapp_webhook(
            [
                whatsapp_message(
                    sender,
                    text=text,
                    message_id=f"wamid.chaos-in-{index}-{time.monotonic_ns()}",
                    extra={"timestamp": str(int(world.clock.now_seconds()))},
                )
            ]
        )
    ).encode()
    response = httpx.post(
        f"{api_url}/v1/channels/meta/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            META_SIGNATURE_HEADER: sign_meta(body),
        },
        timeout=30,
    )
    assert response.status_code == 200, response.text


@dataclass(frozen=True)
class OutboxRow:
    status: str
    attempts: int
    next_attempt_at: int | None


def customer_outbox(world: ChaosWorld) -> list[OutboxRow]:
    """The outbox rows of replies to WhatsApp customers."""

    return [
        OutboxRow(
            status=str(row[0]),
            attempts=int(row[1] or 0),
            next_attempt_at=None if row[2] is None else int(row[2]),
        )
        for row in world.query(
            "select document ->> 'status', document ->> 'attempts', "
            "document ->> 'next_attempt_at' from workshop.outbound_messages "
            "where document -> 'customer' ->> 'channel' = 'whatsapp'"
        )
    ]
