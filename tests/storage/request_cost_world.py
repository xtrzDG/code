"""
The real application over a small load dataset on Postgres, its two pools
traced (`statement_trace`): what one request of each hot kind costs the
database, over the tenant and the platform role together. The requests
are the perf suite's (tests/perf), the dataset a small `workshop
seed-load`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from httpx2 import Response

from app.clients.postgres.postgres_connection_pools import PostgresConnectionPools
from app.containers.app import AppContainer
from app.schemas.dto.load_data import (
    LoadBusinessSeed,
    LoadSeedManifest,
    SeedLoadCommand,
)
from tests.e2e.harness import Workshop, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT, START
from tests.e2e.workshop_container import replace_provider
from tests.storage.postgres_roles import RoleDatabase
from tests.storage.statement_trace import TraceCount, traced_pools, traced_together

SMALL_DATASET: SeedLoadCommand = SeedLoadCommand.model_validate(
    {
        "business_count": 3,
        "message_count": 600,
        "booking_count": 60,
        "visitor_count": 6,
    }
)
TELEGRAM_CHAT_ID: int = 700000001


@dataclass
class RequestCostWorld:
    """The application, its traced pools and the stored dataset."""

    client: TestClient
    pools: PostgresConnectionPools
    manifest: LoadSeedManifest
    update_ids: list[int]
    workshop: Workshop

    @property
    def business(self) -> LoadBusinessSeed:
        return self.manifest.businesses[0]

    @property
    def telegram_business(self) -> LoadBusinessSeed:
        return next(
            entry
            for entry in self.manifest.businesses
            if entry.telegram_channel_id is not None
        )

    def cost(self, send: Callable[[RequestCostWorld], Response]) -> TraceCount:
        """The second of two requests (the first warms caches and writes
        what a first visit writes: an audit entry, a session's use)."""

        first: Response = send(self)
        assert first.status_code == 200, first.text
        with traced_together(self.pools) as count:
            second: Response = send(self)
        assert second.status_code == 200, second.text
        return count


def open_request_cost_world(role_urls: RoleDatabase) -> RequestCostWorld:
    pools = traced_pools(role_urls.tenant_url, role_urls.platform_url, max_size=8)

    def use_traced_pools(container: AppContainer) -> None:
        replace_provider(container.clients.postgres_pools, pools)

    workshop = start_workshop(
        {**E2E_ENVIRONMENT, **role_urls.environment()}, prepare=use_traced_pools
    )
    manifest: LoadSeedManifest = (
        workshop.container.operators.demo.seed_load_operator().operate(SMALL_DATASET)
    )
    # No lifespan: no background thread adds statements to the counts.
    return RequestCostWorld(
        client=TestClient(workshop.application),
        pools=pools,
        manifest=manifest,
        update_ids=[],
        workshop=workshop,
    )


def owner(entry: LoadBusinessSeed) -> dict[str, str]:
    return {"Authorization": f"Bearer {entry.owner_access_token}"}


def get_me(world: RequestCostWorld) -> Response:
    return world.client.get("/v1/me", headers=owner(world.business))


def list_conversations(world: RequestCostWorld) -> Response:
    entry = world.business
    return world.client.get(
        f"/v1/businesses/{entry.business_id}/conversations", headers=owner(entry)
    )


def get_conversation(world: RequestCostWorld) -> Response:
    entry = world.business
    return world.client.get(
        f"/v1/businesses/{entry.business_id}/conversations/{entry.conversation_ids[0]}",
        headers=owner(entry),
    )


def check_availability(world: RequestCostWorld) -> Response:
    entry = world.business
    return world.client.get(
        f"/v1/businesses/{entry.business_id}/availability",
        params={
            "date": (START + timedelta(days=1)).date().isoformat(),
            "party_size": "2",
        },
        headers=owner(entry),
    )


def get_dashboard(world: RequestCostWorld) -> Response:
    entry = world.business
    return world.client.get(
        f"/v1/businesses/{entry.business_id}/dashboard", headers=owner(entry)
    )


def poll_widget(world: RequestCostWorld) -> Response:
    entry = world.business
    visitor = entry.visitors[0]
    return world.client.get(
        f"/v1/widget/{entry.business_id}/messages",
        params={"after": str(visitor.latest_message_id)},
        headers={"X-Widget-Session-Key": str(visitor.session_key)},
    )


def send_telegram_message(world: RequestCostWorld) -> Response:
    """A new customer message each time (a redelivery would be a duplicate)."""

    entry = world.telegram_business
    update_id: int = 9_000 + len(world.update_ids)
    world.update_ids.append(update_id)
    update: dict[str, Any] = {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": int(START.timestamp()),
            "chat": {"id": TELEGRAM_CHAT_ID, "type": "private"},
            "from": {"id": TELEGRAM_CHAT_ID, "first_name": "Load"},
            "text": "Hello! Are you open tonight?",
        },
    }
    return world.client.post(
        f"/v1/channels/telegram/{entry.telegram_channel_id}/webhook",
        json=update,
        headers={"X-Telegram-Bot-Api-Secret-Token": str(entry.telegram_webhook_secret)},
    )
