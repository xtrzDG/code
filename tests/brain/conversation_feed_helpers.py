"""A cabinet HTTP client over a brain world and a few seeded conversations."""

from fastapi.testclient import TestClient

from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld
from tests.brain.cabinet_fakes import UnusedMenuExtractor
from tests.brain.cabinet_http import build_cabinet_client


def cabinet(world: BrainWorld) -> TestClient:
    return build_cabinet_client(
        world,
        UnusedMenuExtractor(),
        {"owner": world.owner_id, "staff": world.staff_id, "stranger": UserId()},
    )


def seed_conversations(world: BrainWorld) -> None:
    world.send("Здравствуйте, есть столик?", name="Нино")
    world.send(
        "Hi from Telegram",
        channel=ChannelKind.TELEGRAM,
        user_id="tg-1",
        phone=None,
    )
    world.send("Sandbox check", is_sandbox=True, user_id="autotest", phone=None)
