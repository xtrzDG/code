"""A cabinet client over a brain world, and a feed of seeded conversations."""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.channels import ChannelDocument, WhatsAppStaffTemplate
from app.schemas.dto.menu_import import MenuExtraction, MenuExtractionRequest
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.prefixed_id import UserId
from tests.brain.brain_world import BrainWorld
from tests.brain.cabinet_fakes import CabinetStorage
from tests.brain.cabinet_http import bearer, build_cabinet_client

DAY_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000


class UnusedMenuExtractor:
    def extract(self, request: MenuExtractionRequest) -> MenuExtraction:
        raise AssertionError("Menu extraction is not part of these tests.")


class Cabinet:
    def __init__(self, world: BrainWorld) -> None:
        self.world = world
        self.storage = CabinetStorage()
        self.client: TestClient = build_cabinet_client(
            world,
            UnusedMenuExtractor(),
            {"owner": world.owner_id, "staff": world.staff_id, "stranger": UserId()},
            self.storage,
        )

    def url(self, path: str = "") -> str:
        return f"/v1/businesses/{self.world.business.id}/conversations{path}"

    def feed(self, token: str = "staff", **params: str) -> dict[str, Any]:
        response = self.client.get(self.url(), params=params, headers=bearer(token))
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    def names(self, **params: str) -> list[str | None]:
        return [row["contact_name"] for row in self.feed(**params)["items"]]

    def card(self, conversation_id: ConversationId) -> dict[str, Any]:
        response = self.client.get(
            self.url(f"/{conversation_id}"), headers=bearer("owner")
        )
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    def reply(
        self,
        conversation_id: ConversationId,
        text: str,
        token: str = "staff",
        as_template: bool | None = None,
    ) -> Any:
        body: dict[str, Any] = {"text": text}
        if as_template is not None:
            body["as_template"] = as_template
        return self.client.post(
            self.url(f"/{conversation_id}/messages"),
            json=body,
            headers=bearer(token),
        )

    def connect(
        self,
        kind: ChannelKind,
        status: ChannelStatus = ChannelStatus.CONNECTED,
        staff_template: WhatsAppStaffTemplate | None = None,
    ) -> None:
        self.world.channel_repo.save(
            ChannelDocument(
                business_id=self.world.business.id,
                kind=kind,
                status=status,
                whatsapp_staff_template=staff_template,
            )
        )


def seed_feed(world: BrainWorld) -> dict[str, ConversationId]:
    """Four customers on three days, with names and texts in three scripts."""

    ids: dict[str, ConversationId] = {}
    ids["nino"] = world.send(
        "Столик на субботу?",
        name="Ниноʼ Беридзе",
        user_id="995599112233",
        phone=E164PhoneNumber("+995599112233"),
    ).conversation_id
    world.clock.advance(timedelta(days=1))
    ids["jose"] = world.send(
        "Hola, ¿tienen mesa?",
        channel=ChannelKind.TELEGRAM,
        user_id="tg-jose",
        name="José",
        phone=None,
    ).conversation_id
    world.clock.advance(timedelta(days=1))
    ids["giorgi"] = world.send(
        "გამარჯობა, ხინკალი გაქვთ?",
        user_id="995577001122",
        name="Giorgi",
        phone=None,
    ).conversation_id
    ids["test"] = world.send(
        "Sandbox", is_sandbox=True, user_id="autotest", phone=None
    ).conversation_id
    for conversation in world.conversations():
        if conversation.id == ids["nino"]:
            conversation.status = ConversationStatus.HANDOFF
            world.conversation_repo.save(conversation)

    return ids
